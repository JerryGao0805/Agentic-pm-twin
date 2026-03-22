"""Integration tests exercising the full API flow through multiple endpoints.

These tests wire up fake services to verify complete user journeys:
  register -> list boards -> create board -> update board -> rename -> delete
  login -> access boards -> chat history
"""
from copy import deepcopy
from typing import Any

from fastapi.testclient import TestClient

import app.main as main_module
from app.config import settings
from app.kanban import default_board


class FakeUserRepository:
    def __init__(self):
        self.users: dict[str, dict] = {}
        self._next_id = 1

    def create_user(self, username: str, password: str) -> int:
        user_id = self._next_id
        self._next_id += 1
        self.users[username] = {
            "id": user_id,
            "username": username,
            "password_hash": f"hashed_{password}",
        }
        return user_id

    def get_user_by_username(self, username: str) -> dict | None:
        return self.users.get(username)

    def verify_password(self, password: str, password_hash: str) -> bool:
        return password_hash == f"hashed_{password}"


class FakeBoardService:
    def __init__(self) -> None:
        self._boards: dict[int, dict[str, Any]] = {}
        self._board_owners: dict[int, str] = {}
        self._next_id = 1

    def list_boards(self, username: str) -> list[dict[str, Any]]:
        return [
            {"id": bid, "name": b.get("name", "Board"), "updated_at": "2026-01-01"}
            for bid, b in self._boards.items()
            if self._board_owners.get(bid) == username
        ]

    def get_board(self, username: str, board_id: int | None = None) -> dict[str, Any] | None:
        if board_id is not None:
            if board_id not in self._boards or self._board_owners.get(board_id) != username:
                return None
            return deepcopy(self._boards[board_id])
        board = default_board()
        return board

    def create_board(self, username: str, name: str, template: str | None = None) -> dict[str, Any]:
        board = default_board()
        bid = self._next_id
        self._next_id += 1
        board["id"] = bid
        board["name"] = name
        self._boards[bid] = board
        self._board_owners[bid] = username
        return deepcopy(board)

    def save_board(self, username: str, board: Any, board_id: int | None = None) -> dict[str, Any] | None:
        payload = board.model_dump() if hasattr(board, "model_dump") else deepcopy(board)
        if board_id is not None:
            if board_id not in self._boards or self._board_owners.get(board_id) != username:
                return None
            self._boards[board_id] = payload
        return payload

    def delete_board(self, username: str, board_id: int) -> bool:
        if board_id in self._boards and self._board_owners.get(board_id) == username:
            del self._boards[board_id]
            del self._board_owners[board_id]
            return True
        return False

    def rename_board(self, username: str, board_id: int, name: str) -> bool:
        if board_id in self._boards and self._board_owners.get(board_id) == username:
            self._boards[board_id]["name"] = name
            return True
        return False


class FakeActivityService:
    def list_activity(self, board_id, limit=50, offset=0):
        return []

    def log_activity(self, board_id, username, action, details=None):
        pass

    def diff_and_log(self, board_id, username, old_board, new_board):
        pass


class FakeChatService:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    def list_messages(self, username: str, **kwargs) -> list[dict[str, str]]:
        return deepcopy(self.messages)

    def append_message(self, username: str, role: str, content: str, **kwargs) -> None:
        self.messages.append({"role": role, "content": content.strip()})


def _setup_services(monkeypatch):
    fake_user_repo = FakeUserRepository()
    fake_board_service = FakeBoardService()
    fake_chat_service = FakeChatService()
    fake_activity_service = FakeActivityService()
    monkeypatch.setattr(main_module, "user_repository", fake_user_repo)
    monkeypatch.setattr(main_module, "board_service", fake_board_service)
    monkeypatch.setattr(main_module, "chat_service", fake_chat_service)
    monkeypatch.setattr(main_module, "activity_service", fake_activity_service)
    return fake_user_repo, fake_board_service, fake_chat_service


def test_full_register_and_board_crud_flow(monkeypatch) -> None:
    fake_user_repo, fake_board_service, _ = _setup_services(monkeypatch)

    with TestClient(main_module.app) as client:
        # 1. Session is unauthenticated
        r = client.get("/api/auth/session")
        assert r.status_code == 200
        assert r.json()["authenticated"] is False

        # 2. Register new user
        r = client.post(
            "/api/auth/register",
            json={"username": "alice", "password": "password123"},
        )
        assert r.status_code == 200
        assert r.json() == {"authenticated": True, "username": "alice"}

        # 3. Session is now authenticated
        r = client.get("/api/auth/session")
        assert r.status_code == 200
        assert r.json()["authenticated"] is True
        assert r.json()["username"] == "alice"

        # 4. List boards (has default board from registration)
        r = client.get("/api/boards")
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["name"] == "My Board"

        # 5. Create a board
        r = client.post("/api/boards", json={"name": "Sprint 1"})
        assert r.status_code == 201
        board = r.json()
        board_id = board["id"]
        assert board["name"] == "Sprint 1"
        assert "columns" in board

        # 6. List boards (now has two)
        r = client.get("/api/boards")
        assert r.status_code == 200
        boards = r.json()
        assert len(boards) == 2
        assert any(b["name"] == "Sprint 1" for b in boards)

        # 7. Get board by id
        r = client.get(f"/api/boards/{board_id}")
        assert r.status_code == 200
        assert r.json()["name"] == "Sprint 1"

        # 8. Rename board
        r = client.patch(f"/api/boards/{board_id}", json={"name": "Sprint 2"})
        assert r.status_code == 200
        assert r.json()["name"] == "Sprint 2"

        # 9. Create a second board
        r = client.post("/api/boards", json={"name": "Backlog"})
        assert r.status_code == 201
        second_board_id = r.json()["id"]

        # 10. List boards shows three (default + Sprint 2 + Backlog)
        r = client.get("/api/boards")
        assert r.status_code == 200
        assert len(r.json()) == 3

        # 11. Delete second board
        r = client.delete(f"/api/boards/{second_board_id}")
        assert r.status_code == 204

        # 12. List boards shows two again
        r = client.get("/api/boards")
        assert r.status_code == 200
        assert len(r.json()) == 2

        # 13. Logout
        r = client.post("/api/auth/logout")
        assert r.status_code == 200
        assert r.json()["authenticated"] is False

        # 14. Boards endpoint is now 401
        r = client.get("/api/boards")
        assert r.status_code == 401


def test_login_and_access_boards(monkeypatch) -> None:
    fake_user_repo, fake_board_service, _ = _setup_services(monkeypatch)
    # Pre-create a user
    fake_user_repo.create_user("bob", "securepass")

    with TestClient(main_module.app) as client:
        # Login
        r = client.post(
            "/api/auth/login",
            json={"username": "bob", "password": "securepass"},
        )
        assert r.status_code == 200
        assert r.json()["authenticated"] is True

        # Create board
        r = client.post("/api/boards", json={"name": "Bob's Board"})
        assert r.status_code == 201

        # Access it
        r = client.get("/api/boards")
        assert r.status_code == 200
        assert len(r.json()) == 1


def test_register_duplicate_username(monkeypatch) -> None:
    _setup_services(monkeypatch)

    with TestClient(main_module.app) as client:
        r = client.post(
            "/api/auth/register",
            json={"username": "alice", "password": "password123"},
        )
        assert r.status_code == 200

    with TestClient(main_module.app) as client:
        r = client.post(
            "/api/auth/register",
            json={"username": "alice", "password": "otherpass123"},
        )
        assert r.status_code == 409


def test_login_wrong_password(monkeypatch) -> None:
    fake_user_repo, _, _ = _setup_services(monkeypatch)
    fake_user_repo.create_user("charlie", "correct_pass")

    with TestClient(main_module.app) as client:
        r = client.post(
            "/api/auth/login",
            json={"username": "charlie", "password": "wrong_pass"},
        )
        assert r.status_code == 401


def test_rate_limit_on_login(monkeypatch) -> None:
    _setup_services(monkeypatch)

    with TestClient(main_module.app) as client:
        for _ in range(10):
            client.post(
                "/api/auth/login",
                json={"username": "nonexist", "password": "wrong"},
            )

        r = client.post(
            "/api/auth/login",
            json={"username": "nonexist", "password": "wrong"},
        )
        assert r.status_code == 429
        assert "too many" in r.json()["detail"].lower()


def test_rate_limit_on_register(monkeypatch) -> None:
    fake_user_repo, _, _ = _setup_services(monkeypatch)

    with TestClient(main_module.app) as client:
        for i in range(10):
            client.post(
                "/api/auth/register",
                json={"username": f"user{i}", "password": "password123"},
            )

        r = client.post(
            "/api/auth/register",
            json={"username": "onemore", "password": "password123"},
        )
        assert r.status_code == 429


def test_update_board_by_id(monkeypatch) -> None:
    _, fake_board_service, _ = _setup_services(monkeypatch)

    with TestClient(main_module.app) as client:
        client.cookies.set(settings.auth_cookie_name, settings.sign_session("user"))

        # Create board
        r = client.post("/api/boards", json={"name": "Test Board"})
        board_id = r.json()["id"]

        # Update board with modified columns
        board = r.json()
        board["columns"][0]["title"] = "Modified"
        r = client.put(f"/api/boards/{board_id}", json=board)
        assert r.status_code == 200


def test_chat_history_endpoint(monkeypatch) -> None:
    _, _, fake_chat = _setup_services(monkeypatch)
    fake_chat.messages = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]

    with TestClient(main_module.app) as client:
        client.cookies.set(settings.auth_cookie_name, settings.sign_session("user"))
        r = client.get("/api/ai/chat/history")

    assert r.status_code == 200
    assert len(r.json()) == 2
    assert r.json()[0]["role"] == "user"
    assert r.json()[1]["role"] == "assistant"


def test_chat_history_with_board_id(monkeypatch) -> None:
    _, _, fake_chat = _setup_services(monkeypatch)

    with TestClient(main_module.app) as client:
        client.cookies.set(settings.auth_cookie_name, settings.sign_session("user"))
        r = client.get("/api/ai/chat/history?board_id=42")

    assert r.status_code == 200


def test_health_endpoint(monkeypatch) -> None:
    from app.db import probe_mysql
    monkeypatch.setattr(main_module, "probe_mysql", lambda: (True, None))

    with TestClient(main_module.app) as client:
        r = client.get("/api/health")

    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["database"]["connected"] is True


def test_health_endpoint_degraded(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "probe_mysql", lambda: (False, "Connection refused"))

    with TestClient(main_module.app) as client:
        r = client.get("/api/health")

    assert r.status_code == 200
    assert r.json()["status"] == "degraded"


def test_startup_db_error_blocks_authenticated_endpoints(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "board_service", FakeBoardService())

    with TestClient(main_module.app) as client:
        # Set after lifespan runs so it's not overwritten
        main_module.startup_db_error = "Connection refused"
        try:
            client.cookies.set(settings.auth_cookie_name, settings.sign_session("user"))
            r = client.get("/api/boards")
            assert r.status_code == 503
            assert "temporarily unavailable" in r.json()["detail"].lower()
        finally:
            main_module.startup_db_error = None


def test_create_board_validation(monkeypatch) -> None:
    _setup_services(monkeypatch)

    with TestClient(main_module.app) as client:
        client.cookies.set(settings.auth_cookie_name, settings.sign_session("user"))

        # Empty name should be rejected
        r = client.post("/api/boards", json={"name": ""})
        assert r.status_code == 422

        # Missing name
        r = client.post("/api/boards", json={})
        assert r.status_code == 422


def test_register_validation(monkeypatch) -> None:
    _setup_services(monkeypatch)

    with TestClient(main_module.app) as client:
        # Username too short
        r = client.post(
            "/api/auth/register",
            json={"username": "a", "password": "password123"},
        )
        assert r.status_code == 422

        # Password too short
        r = client.post(
            "/api/auth/register",
            json={"username": "validuser", "password": "12345"},
        )
        assert r.status_code == 422

        # Missing fields
        r = client.post("/api/auth/register", json={})
        assert r.status_code == 422


def test_legacy_board_endpoint_still_works(monkeypatch) -> None:
    _, fake_board_service, _ = _setup_services(monkeypatch)

    with TestClient(main_module.app) as client:
        client.cookies.set(settings.auth_cookie_name, settings.sign_session("user"))

        # Legacy GET /api/board still works
        r = client.get("/api/board")
        assert r.status_code == 200
        assert "columns" in r.json()

        # Legacy PUT /api/board still works
        board = default_board()
        r = client.put("/api/board", json=board)
        assert r.status_code == 200


def test_get_nonexistent_board_returns_404(monkeypatch) -> None:
    _setup_services(monkeypatch)

    with TestClient(main_module.app) as client:
        client.cookies.set(settings.auth_cookie_name, settings.sign_session("user"))
        r = client.get("/api/boards/999")

    assert r.status_code == 404
    assert r.json()["detail"] == "Board not found."


def test_put_nonexistent_board_returns_404(monkeypatch) -> None:
    _setup_services(monkeypatch)

    with TestClient(main_module.app) as client:
        client.cookies.set(settings.auth_cookie_name, settings.sign_session("user"))
        board = default_board()
        r = client.put("/api/boards/999", json=board)

    assert r.status_code == 404
    assert r.json()["detail"] == "Board not found."


def test_board_isolation_between_users(monkeypatch) -> None:
    """Boards created by one user should not be accessible by another."""
    fake_user_repo, fake_board_service, _ = _setup_services(monkeypatch)

    with TestClient(main_module.app) as client:
        # Register alice and create a board
        client.post(
            "/api/auth/register",
            json={"username": "alice", "password": "password123"},
        )
        r = client.post("/api/boards", json={"name": "Alice Board"})
        assert r.status_code == 201
        alice_board_id = r.json()["id"]

        # Logout
        client.post("/api/auth/logout")

        # Register bob
        client.post(
            "/api/auth/register",
            json={"username": "bob", "password": "password123"},
        )

        # Bob should only see his own default board, not Alice's
        r = client.get("/api/boards")
        assert r.status_code == 200
        bob_boards = r.json()
        assert len(bob_boards) == 1
        assert bob_boards[0]["name"] == "My Board"
        assert all(b["id"] != alice_board_id for b in bob_boards)

        # Bob should not be able to access Alice's board by ID
        r = client.get(f"/api/boards/{alice_board_id}")
        assert r.status_code == 404


def test_put_board_with_id_and_name_metadata(monkeypatch) -> None:
    """Frontend sends board with id and name fields; these should be accepted."""
    _, fake_board_service, _ = _setup_services(monkeypatch)

    with TestClient(main_module.app) as client:
        client.cookies.set(settings.auth_cookie_name, settings.sign_session("user"))

        # Create board first
        r = client.post("/api/boards", json={"name": "Test"})
        board = r.json()
        board_id = board["id"]

        # Update with id/name metadata (as frontend does)
        board["columns"][0]["title"] = "Updated"
        r = client.put(f"/api/boards/{board_id}", json=board)
        assert r.status_code == 200
