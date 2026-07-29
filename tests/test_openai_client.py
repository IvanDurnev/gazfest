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
    assert "Ярче звезд" in FESTIVAL_ASSISTANT_INSTRUCTIONS


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
