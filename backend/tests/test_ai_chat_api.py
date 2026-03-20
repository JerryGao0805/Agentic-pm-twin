from copy import deepcopy

from fastapi.testclient import TestClient

import app.main as main_module
from app.config import settings
from app.kanban import BoardPayload, default_board
from app.services.ai_assistant_service import AIAssistantFormatError, AIAssistantOutput
from app.services.openai_service import OpenAIConfigError


class FakeBoardService:
    def __init__(self) -> None:
        self.board = default_board()

    def get_board(self, username: str, board_id: int | None = None) -> dict:
        return deepcopy(self.board)

    def save_board(self, username: str, board: dict, board_id: int | None = None) -> dict | None:
        validated = BoardPayload.model_validate(
            {k: v for k, v in board.items() if k not in ("id", "name")}
        ).model_dump()
        self.board = deepcopy(validated)
        return deepcopy(validated)

    def list_boards(self, username: str) -> list:
        return []

    def create_board(self, username: str, name: str) -> dict:
        return default_board()

    def delete_board(self, username: str, board_id: int) -> bool:
        return False

    def rename_board(self, username: str, board_id: int, name: str) -> bool:
        return False


class FakeChatService:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    def list_messages(self, username: str, **kwargs) -> list[dict[str, str]]:
        return deepcopy(self.messages)

    def append_message(self, username: str, role: str, content: str, **kwargs) -> None:
        self.messages.append({"role": role, "content": content.strip()})


class FakeAIAssistantService:
    def __init__(self, mode: str = "text_only") -> None:
        self.mode = mode

    def generate_reply(self, board: dict, chat_history: list[dict[str, str]], user_message: str):
        if self.mode == "text_only":
            return AIAssistantOutput(
                assistant_message="No board updates needed.",
                board=None,
            )

        if self.mode == "valid_board":
            updated = deepcopy(board)
            updated["columns"][0]["title"] = "Ideas"
            return AIAssistantOutput(
                assistant_message="Renamed backlog to Ideas.",
                board=updated,
            )

        invalid = deepcopy(board)
        # Make invalid by removing all columns
        invalid["columns"] = []
        return AIAssistantOutput(
            assistant_message="I tried to update the board.",
            board=invalid,
        )


class FailingAIAssistantService:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def generate_reply(self, board: dict, chat_history: list[dict[str, str]], user_message: str):
        raise self.error


def _with_auth_cookie(client: TestClient) -> None:
    client.cookies.set(settings.auth_cookie_name, settings.sign_session(settings.auth_username))


def test_ai_chat_requires_authentication(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "board_service", FakeBoardService())
    monkeypatch.setattr(main_module, "chat_service", FakeChatService())
    monkeypatch.setattr(main_module, "ai_assistant_service", FakeAIAssistantService())

    with TestClient(main_module.app) as client:
        response = client.post("/api/ai/chat", json={"message": "Help"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}


def test_ai_chat_history_requires_authentication(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "chat_service", FakeChatService())

    with TestClient(main_module.app) as client:
        response = client.get("/api/ai/chat/history")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}


def test_ai_chat_history_returns_persisted_messages(monkeypatch) -> None:
    fake_chat_service = FakeChatService()
    fake_chat_service.append_message("user", "user", "hello")
    fake_chat_service.append_message("user", "assistant", "hi")
    monkeypatch.setattr(main_module, "chat_service", fake_chat_service)

    with TestClient(main_module.app) as client:
        _with_auth_cookie(client)
        response = client.get("/api/ai/chat/history")

    assert response.status_code == 200
    assert response.json() == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]


def test_ai_chat_text_only_response_keeps_board_and_appends_history(monkeypatch) -> None:
    fake_board_service = FakeBoardService()
    fake_chat_service = FakeChatService()

    monkeypatch.setattr(main_module, "board_service", fake_board_service)
    monkeypatch.setattr(main_module, "chat_service", fake_chat_service)
    monkeypatch.setattr(
        main_module,
        "ai_assistant_service",
        FakeAIAssistantService(mode="text_only"),
    )

    with TestClient(main_module.app) as client:
        _with_auth_cookie(client)
        response = client.post(
            "/api/ai/chat",
            json={"message": "What should I focus on today?"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "No board updates needed."
    assert payload["board_updated"] is False
    assert payload["board_update_error"] is None
    assert payload["chat_history"] == [
        {"role": "user", "content": "What should I focus on today?"},
        {"role": "assistant", "content": "No board updates needed."},
    ]
    assert payload["board"]["columns"][0]["title"] == "Backlog"


def test_ai_chat_valid_board_response_persists_board(monkeypatch) -> None:
    fake_board_service = FakeBoardService()
    fake_chat_service = FakeChatService()

    monkeypatch.setattr(main_module, "board_service", fake_board_service)
    monkeypatch.setattr(main_module, "chat_service", fake_chat_service)
    monkeypatch.setattr(
        main_module,
        "ai_assistant_service",
        FakeAIAssistantService(mode="valid_board"),
    )

    with TestClient(main_module.app) as client:
        _with_auth_cookie(client)
        response = client.post(
            "/api/ai/chat",
            json={"message": "Rename backlog to Ideas."},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "Renamed backlog to Ideas."
    assert payload["board_updated"] is True
    assert payload["board_update_error"] is None
    assert payload["board"]["columns"][0]["title"] == "Ideas"
    assert fake_board_service.board["columns"][0]["title"] == "Ideas"


def test_ai_chat_invalid_board_response_keeps_text_and_skips_update(monkeypatch) -> None:
    fake_board_service = FakeBoardService()
    fake_chat_service = FakeChatService()

    monkeypatch.setattr(main_module, "board_service", fake_board_service)
    monkeypatch.setattr(main_module, "chat_service", fake_chat_service)
    monkeypatch.setattr(
        main_module,
        "ai_assistant_service",
        FakeAIAssistantService(mode="invalid_board"),
    )

    with TestClient(main_module.app) as client:
        _with_auth_cookie(client)
        response = client.post(
            "/api/ai/chat",
            json={"message": "Move every card to done."},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "I tried to update the board."
    assert payload["board_updated"] is False
    assert payload["board_update_error"] == (
        "AI proposed an invalid board update; update was skipped."
    )
    assert payload["board"]["columns"][0]["id"] == "col-backlog"
    assert fake_board_service.board["columns"][0]["id"] == "col-backlog"
    assert payload["chat_history"][-1] == {
        "role": "assistant",
        "content": "I tried to update the board.",
    }


def test_ai_chat_returns_503_for_missing_openai_key(monkeypatch) -> None:
    fake_chat_service = FakeChatService()
    monkeypatch.setattr(main_module, "board_service", FakeBoardService())
    monkeypatch.setattr(main_module, "chat_service", fake_chat_service)
    monkeypatch.setattr(
        main_module,
        "ai_assistant_service",
        FailingAIAssistantService(OpenAIConfigError("OPENAI_API_KEY is not configured.")),
    )

    with TestClient(main_module.app) as client:
        _with_auth_cookie(client)
        response = client.post("/api/ai/chat", json={"message": "Hello"})

    assert response.status_code == 503
    assert response.json() == {"detail": "OPENAI_API_KEY is not configured."}
    assert fake_chat_service.messages == [], "User message must not be saved when AI call fails"


def test_ai_chat_returns_502_for_invalid_ai_schema(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "board_service", FakeBoardService())
    monkeypatch.setattr(main_module, "chat_service", FakeChatService())
    monkeypatch.setattr(
        main_module,
        "ai_assistant_service",
        FailingAIAssistantService(
            AIAssistantFormatError("AI response did not match expected schema.")
        ),
    )

    with TestClient(main_module.app) as client:
        _with_auth_cookie(client)
        response = client.post("/api/ai/chat", json={"message": "Hello"})

    assert response.status_code == 502
    assert response.json() == {"detail": "AI response did not match expected schema."}
