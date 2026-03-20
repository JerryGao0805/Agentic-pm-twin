from typing import Any

from fastapi.testclient import TestClient
from mysql.connector import Error as MySQLError

import app.main as main_module
from app.config import settings
from app.kanban import BoardPayload, default_board


class FailingBoardService:
    def get_board(self, username: str, board_id: int | None = None) -> dict[str, Any]:
        raise MySQLError("Connection refused")

    def save_board(self, username: str, board: Any, board_id: int | None = None) -> dict[str, Any]:
        raise MySQLError("Connection refused")

    def list_boards(self, username: str) -> list[dict[str, Any]]:
        raise MySQLError("Connection refused")

    def create_board(self, username: str, name: str) -> dict[str, Any]:
        raise MySQLError("Connection refused")

    def delete_board(self, username: str, board_id: int) -> bool:
        raise MySQLError("Connection refused")

    def rename_board(self, username: str, board_id: int, name: str) -> bool:
        raise MySQLError("Connection refused")


class FakeBoardService:
    def __init__(self) -> None:
        self.saved_payload: dict[str, Any] | None = None
        self._boards: dict[int, dict[str, Any]] = {}
        self._next_id = 1

    def list_boards(self, username: str) -> list[dict[str, Any]]:
        return [
            {"id": bid, "name": b.get("name", "Board"), "updated_at": "2026-01-01"}
            for bid, b in self._boards.items()
        ]

    def get_board(self, username: str, board_id: int | None = None) -> dict[str, Any] | None:
        if board_id is not None:
            return self._boards.get(board_id)
        board = default_board()
        board["columns"][0]["title"] = f"Backlog ({username})"
        return board

    def create_board(self, username: str, name: str) -> dict[str, Any]:
        board = default_board()
        bid = self._next_id
        self._next_id += 1
        board["id"] = bid
        board["name"] = name
        self._boards[bid] = board
        return board

    def save_board(self, username: str, board: Any, board_id: int | None = None) -> dict[str, Any]:
        if isinstance(board, dict):
            board_data = {k: v for k, v in board.items() if k not in ("id", "name")}
            validated = BoardPayload.model_validate(board_data)
            payload = validated.model_dump()
        elif hasattr(board, "model_dump"):
            payload = board.model_dump()
        else:
            payload = board
        self.saved_payload = payload
        return payload

    def delete_board(self, username: str, board_id: int) -> bool:
        if board_id in self._boards:
            del self._boards[board_id]
            return True
        return False

    def rename_board(self, username: str, board_id: int, name: str) -> bool:
        if board_id in self._boards:
            self._boards[board_id]["name"] = name
            return True
        return False


def test_get_board_requires_authentication(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "board_service", FakeBoardService())

    with TestClient(main_module.app) as client:
        response = client.get("/api/board")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}


def test_get_board_returns_board_for_authenticated_user(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "board_service", FakeBoardService())

    with TestClient(main_module.app) as client:
        client.cookies.set(settings.auth_cookie_name, settings.sign_session(settings.auth_username))
        response = client.get("/api/board")

    assert response.status_code == 200
    payload = response.json()
    assert payload["columns"][0]["id"] == "col-backlog"
    assert payload["columns"][0]["title"] == f"Backlog ({settings.auth_username})"


def test_put_board_rejects_invalid_structure(monkeypatch) -> None:
    fake_service = FakeBoardService()
    monkeypatch.setattr(main_module, "board_service", fake_service)

    # Board with no columns should be rejected
    invalid_board = {"columns": [], "cards": {}}

    with TestClient(main_module.app) as client:
        client.cookies.set(settings.auth_cookie_name, settings.sign_session(settings.auth_username))
        response = client.put("/api/board", json=invalid_board)

    assert response.status_code == 422
    assert fake_service.saved_payload is None


def test_put_board_saves_valid_payload(monkeypatch) -> None:
    fake_service = FakeBoardService()
    monkeypatch.setattr(main_module, "board_service", fake_service)

    board = default_board()
    board["columns"][0]["title"] = "Ideas"

    with TestClient(main_module.app) as client:
        client.cookies.set(settings.auth_cookie_name, settings.sign_session(settings.auth_username))
        response = client.put("/api/board", json=board)

    assert response.status_code == 200
    assert response.json()["columns"][0]["title"] == "Ideas"
    assert fake_service.saved_payload is not None
    assert fake_service.saved_payload["columns"][0]["title"] == "Ideas"


def test_get_board_returns_503_on_database_error(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "board_service", FailingBoardService())

    with TestClient(main_module.app, raise_server_exceptions=False) as client:
        client.cookies.set(settings.auth_cookie_name, settings.sign_session(settings.auth_username))
        response = client.get("/api/board")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database temporarily unavailable."}


def test_put_board_returns_503_on_database_error(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "board_service", FailingBoardService())

    board = default_board()

    with TestClient(main_module.app, raise_server_exceptions=False) as client:
        client.cookies.set(settings.auth_cookie_name, settings.sign_session(settings.auth_username))
        response = client.put("/api/board", json=board)

    assert response.status_code == 503
    assert response.json() == {"detail": "Database temporarily unavailable."}


# --- Multi-board API tests ---

def test_list_boards_requires_auth(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "board_service", FakeBoardService())

    with TestClient(main_module.app) as client:
        response = client.get("/api/boards")

    assert response.status_code == 401


def test_create_board(monkeypatch) -> None:
    fake_service = FakeBoardService()
    monkeypatch.setattr(main_module, "board_service", fake_service)

    with TestClient(main_module.app) as client:
        client.cookies.set(settings.auth_cookie_name, settings.sign_session(settings.auth_username))
        response = client.post("/api/boards", json={"name": "Sprint Board"})

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "Sprint Board"
    assert "id" in payload


def test_get_board_by_id(monkeypatch) -> None:
    fake_service = FakeBoardService()
    fake_service.create_board("user", "Test Board")
    monkeypatch.setattr(main_module, "board_service", fake_service)

    with TestClient(main_module.app) as client:
        client.cookies.set(settings.auth_cookie_name, settings.sign_session(settings.auth_username))
        response = client.get("/api/boards/1")

    assert response.status_code == 200
    assert response.json()["name"] == "Test Board"


def test_get_board_by_id_returns_404_when_missing(monkeypatch) -> None:
    fake_service = FakeBoardService()
    monkeypatch.setattr(main_module, "board_service", fake_service)

    with TestClient(main_module.app) as client:
        client.cookies.set(settings.auth_cookie_name, settings.sign_session(settings.auth_username))
        response = client.get("/api/boards/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Board not found."


def test_delete_board(monkeypatch) -> None:
    fake_service = FakeBoardService()
    fake_service.create_board("user", "To Delete")
    monkeypatch.setattr(main_module, "board_service", fake_service)

    with TestClient(main_module.app) as client:
        client.cookies.set(settings.auth_cookie_name, settings.sign_session(settings.auth_username))
        response = client.delete("/api/boards/1")

    assert response.status_code == 204


def test_delete_nonexistent_board_returns_404(monkeypatch) -> None:
    fake_service = FakeBoardService()
    monkeypatch.setattr(main_module, "board_service", fake_service)

    with TestClient(main_module.app) as client:
        client.cookies.set(settings.auth_cookie_name, settings.sign_session(settings.auth_username))
        response = client.delete("/api/boards/999")

    assert response.status_code == 404


def test_rename_board(monkeypatch) -> None:
    fake_service = FakeBoardService()
    fake_service.create_board("user", "Old Name")
    monkeypatch.setattr(main_module, "board_service", fake_service)

    with TestClient(main_module.app) as client:
        client.cookies.set(settings.auth_cookie_name, settings.sign_session(settings.auth_username))
        response = client.patch("/api/boards/1", json={"name": "New Name"})

    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


def test_rename_nonexistent_board_returns_404(monkeypatch) -> None:
    fake_service = FakeBoardService()
    monkeypatch.setattr(main_module, "board_service", fake_service)

    with TestClient(main_module.app) as client:
        client.cookies.set(settings.auth_cookie_name, settings.sign_session(settings.auth_username))
        response = client.patch("/api/boards/999", json={"name": "New Name"})

    assert response.status_code == 404


def test_put_board_with_custom_columns(monkeypatch) -> None:
    fake_service = FakeBoardService()
    monkeypatch.setattr(main_module, "board_service", fake_service)

    board = {
        "columns": [
            {"id": "col-todo", "title": "To Do", "cardIds": ["c1"]},
            {"id": "col-doing", "title": "Doing", "cardIds": []},
        ],
        "cards": {
            "c1": {"id": "c1", "title": "A task", "details": "Details"},
        },
    }

    with TestClient(main_module.app) as client:
        client.cookies.set(settings.auth_cookie_name, settings.sign_session(settings.auth_username))
        response = client.put("/api/board", json=board)

    assert response.status_code == 200
    assert len(response.json()["columns"]) == 2


def test_put_board_with_card_priority(monkeypatch) -> None:
    fake_service = FakeBoardService()
    monkeypatch.setattr(main_module, "board_service", fake_service)

    board = {
        "columns": [
            {"id": "col-1", "title": "Todo", "cardIds": ["c1"]},
        ],
        "cards": {
            "c1": {
                "id": "c1",
                "title": "Task",
                "details": "Details",
                "priority": "high",
                "due_date": "2026-04-01",
                "assignee": "bob",
            },
        },
    }

    with TestClient(main_module.app) as client:
        client.cookies.set(settings.auth_cookie_name, settings.sign_session(settings.auth_username))
        response = client.put("/api/board", json=board)

    assert response.status_code == 200
    card = response.json()["cards"]["c1"]
    assert card["priority"] == "high"
    assert card["due_date"] == "2026-04-01"
    assert card["assignee"] == "bob"
