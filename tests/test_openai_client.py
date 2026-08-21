from types import SimpleNamespace
from unittest.mock import Mock

from app.config import Config
from app.openai_client import (
    FESTIVAL_ASSISTANT_INSTRUCTIONS,
    generate_festival_answer,
)


def test_knowledge_contains_festival_facts():
    assert "с 14:00 до 22:00" in FESTIVAL_ASSISTANT_INSTRUCTIONS
    assert "DJ Groove" in FESTIVAL_ASSISTANT_INSTRUCTIONS
    assert "DJ Smash" in FESTIVAL_ASSISTANT_INSTRUCTIONS
    assert "Газпром переработка Благовещенск" in FESTIVAL_ASSISTANT_INSTRUCTIONS
    assert "Время звезд" in FESTIVAL_ASSISTANT_INSTRUCTIONS
    assert "Свободный микрофон" not in FESTIVAL_ASSISTANT_INSTRUCTIONS
    assert "Ты — Геля" in FESTIVAL_ASSISTANT_INSTRUCTIONS
    assert "в женском роде" in FESTIVAL_ASSISTANT_INSTRUCTIONS
    assert "блокировки интернета на объектах АГПЗ" in FESTIVAL_ASSISTANT_INSTRUCTIONS
    assert "другом Метаней" in FESTIVAL_ASSISTANT_INSTRUCTIONS
    assert "в городе — там всё работает хорошо" in FESTIVAL_ASSISTANT_INSTRUCTIONS
    assert "можно подать через миниприложение" in FESTIVAL_ASSISTANT_INSTRUCTIONS
    assert "кнопку слева внизу" in FESTIVAL_ASSISTANT_INSTRUCTIONS
    expected_program = {
        "14:00": "открытие с участием байкеров",
        "15:00": "спортивные заезды «На старт! Внимание! Газ!»",
        "17:00": "шоу талантов «Время звезд» и фестивальное лото",
        "18:00": "официальное открытие",
        "18:10": "приветствия руководителей и администрации города",
        "18:20": "награждение работников предприятия",
        "19:50": "DJ Groove",
        "21:00": "DJ Smash",
        "22:00": "завершение фестиваля",
    }
    for event_time, event_name in expected_program.items():
        assert event_time in FESTIVAL_ASSISTANT_INSTRUCTIONS
        assert event_name in FESTIVAL_ASSISTANT_INSTRUCTIONS


def test_generate_festival_answer_uses_responses_api(monkeypatch):
    create = Mock(return_value=SimpleNamespace(output_text="  Ответ о фестивале  "))
    client = Mock()
    client.responses.create = create
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=None)

    monkeypatch.setattr("app.openai_client.OpenAI", Mock(return_value=client))
    monkeypatch.setattr(Config, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(Config, "OPENAI_MODEL", "gpt-5.6-terra")

    answer = generate_festival_answer("Кто организатор?")

    assert answer == "Ответ о фестивале"
    create.assert_called_once_with(
        model="gpt-5.6-terra",
        instructions=FESTIVAL_ASSISTANT_INSTRUCTIONS,
        input="Кто организатор?",
        max_output_tokens=Config.OPENAI_MAX_OUTPUT_TOKENS,
        store=False,
        reasoning={"effort": "none"},
    )
