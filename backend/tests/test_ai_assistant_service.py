import json

import pytest

from app.kanban import default_board
from app.services.ai_assistant_service import (
    AIAssistantFormatError,
    AIAssistantService,
)


class FakeOpenAIService:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.prompts: list[str] = []

    def get_text_response(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response_text


def test_build_prompt_includes_board_history_and_message() -> None:
    service = AIAssistantService(openai_service=FakeOpenAIService(""))

    prompt = service.build_prompt(
        board=default_board(),
        chat_history=[{"role": "assistant", "content": "Prior summary"}],
        user_message="Move card-1 to review",
    )

    assert "Context JSON" in prompt
    assert '"user_message": "Move card-1 to review"' in prompt
    assert "col-backlog" in prompt
    assert "col-review" in prompt


def test_parse_output_accepts_text_only_response() -> None:
    service = AIAssistantService(openai_service=FakeOpenAIService(""))

    output = service.parse_output(
        '{"assistant_message":"No board changes needed.","board":null}'
    )

    assert output.assistant_message == "No board changes needed."
    assert output.board is None


def test_parse_output_accepts_board_payload_response() -> None:
    service = AIAssistantService(openai_service=FakeOpenAIService(""))

    payload = {
        "assistant_message": "Updated board.",
        "board": default_board(),
    }
    output = service.parse_output(json.dumps(payload))

    assert output.assistant_message == "Updated board."
    assert output.board is not None
    assert output.board["columns"][0]["id"] == "col-backlog"


def test_parse_output_rejects_invalid_schema() -> None:
    service = AIAssistantService(openai_service=FakeOpenAIService(""))

    with pytest.raises(AIAssistantFormatError):
        service.parse_output('{"board":null}')


def test_generate_reply_calls_openai_service_with_prompt() -> None:
    fake_openai = FakeOpenAIService(
        '{"assistant_message":"Done.","board":null}'
    )
    service = AIAssistantService(openai_service=fake_openai)

    output = service.generate_reply(
        board=default_board(),
        chat_history=[],
        user_message="What should I work on next?",
    )

    assert output.assistant_message == "Done."
    assert len(fake_openai.prompts) == 1
    assert "What should I work on next?" in fake_openai.prompts[0]
