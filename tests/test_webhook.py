from unittest.mock import Mock


def make_update(
    text: str | None = "Привет",
    *,
    is_bot: bool = False,
    chat_id: int | None = 123,
) -> dict:
    return {
        "update_type": "message_created",
        "timestamp": 1_722_000_000_000,
        "message": {
            "sender": {
                "user_id": 42,
                "is_bot": is_bot,
            },
            "recipient": {
                "chat_id": chat_id,
                "chat_type": "dialog",
            },
            "body": {
                "mid": "message-id",
                "text": text,
            },
        },
    }


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_miniapp_page(client):
    response = client.get("/max/miniapp")

    assert response.status_code == 200
    assert "ГАЗ!ФЕСТ" in response.text
    assert "Геля на связи" in response.text
    assert "miniapp/images/gelya.png" in response.text


def test_webhook_rejects_wrong_secret(client):
    response = client.post(
        "/max/webhook",
        json=make_update(),
        headers={"X-Max-Bot-Api-Secret": "wrong"},
    )

    assert response.status_code == 401


def test_webhook_enqueues_ai_answer(client, monkeypatch):
    redis = Mock()
    redis.set.return_value = True
    task = Mock()

    monkeypatch.setattr("app.routes.get_redis", lambda: redis)
    monkeypatch.setattr("app.routes.answer_message", task)

    response = client.post(
        "/max/webhook",
        json=make_update(),
        headers={"X-Max-Bot-Api-Secret": "test-secret"},
    )

    assert response.status_code == 200
    assert response.json == {"status": "queued"}
    task.delay.assert_called_once_with(
        text="Привет",
        chat_id=123,
        user_id=42,
    )


def test_webhook_uses_sender_for_direct_message(client, monkeypatch):
    redis = Mock()
    redis.set.return_value = True
    task = Mock()

    monkeypatch.setattr("app.routes.get_redis", lambda: redis)
    monkeypatch.setattr("app.routes.answer_message", task)

    response = client.post(
        "/max/webhook",
        json=make_update(chat_id=None),
        headers={"X-Max-Bot-Api-Secret": "test-secret"},
    )

    assert response.status_code == 200
    task.delay.assert_called_once_with(
        text="Привет",
        chat_id=None,
        user_id=42,
    )


def test_webhook_ignores_bot_messages(client, monkeypatch):
    task = Mock()
    monkeypatch.setattr("app.routes.answer_message", task)

    response = client.post(
        "/max/webhook",
        json=make_update(is_bot=True),
        headers={"X-Max-Bot-Api-Secret": "test-secret"},
    )

    assert response.status_code == 200
    assert response.json == {"status": "ignored"}
    task.delay.assert_not_called()


def test_webhook_ignores_duplicate(client, monkeypatch):
    redis = Mock()
    redis.set.return_value = None
    task = Mock()

    monkeypatch.setattr("app.routes.get_redis", lambda: redis)
    monkeypatch.setattr("app.routes.answer_message", task)

    response = client.post(
        "/max/webhook",
        json=make_update(),
        headers={"X-Max-Bot-Api-Secret": "test-secret"},
    )

    assert response.status_code == 200
    assert response.json == {"status": "duplicate"}
    task.delay.assert_not_called()


def test_start_command_enqueues_main_menu(client, monkeypatch):
    redis = Mock()
    redis.set.return_value = True
    menu_task = Mock()
    answer_task = Mock()

    monkeypatch.setattr("app.routes.get_redis", lambda: redis)
    monkeypatch.setattr("app.routes.send_main_menu", menu_task)
    monkeypatch.setattr("app.routes.answer_message", answer_task)

    response = client.post(
        "/max/webhook",
        json=make_update(text="/start"),
        headers={"X-Max-Bot-Api-Secret": "test-secret"},
    )

    assert response.status_code == 200
    menu_task.delay.assert_called_once_with(chat_id=123, user_id=42)
    answer_task.delay.assert_not_called()


def test_bot_started_enqueues_main_menu(client, monkeypatch):
    redis = Mock()
    redis.set.return_value = True
    task = Mock()

    monkeypatch.setattr("app.routes.get_redis", lambda: redis)
    monkeypatch.setattr(
        "app.routes.register_user_and_send_main_menu",
        task,
    )

    response = client.post(
        "/max/webhook",
        json={
            "update_type": "bot_started",
            "timestamp": 1_722_000_000_000,
            "chat_id": 123,
            "user": {
                "user_id": 42,
                "first_name": "Иван",
                "last_name": "Иванов",
                "username": "ivan",
                "is_bot": False,
            },
        },
        headers={"X-Max-Bot-Api-Secret": "test-secret"},
    )

    assert response.status_code == 200
    task.delay.assert_called_once_with(
        max_user_id=42,
        chat_id=123,
        timestamp=1_722_000_000_000,
        first_name="Иван",
        last_name="Иванов",
        username="ivan",
    )
