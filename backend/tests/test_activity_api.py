"""Tests for board activity log API and diff_and_log detection."""
from typing import Any

from fastapi.testclient import TestClient

import app.main as main_module
from app.config import settings
from app.kanban import default_board
from app.services.activity_service import ActivityService


class FakeActivityRepository:
    def __init__(self):
        self._entries: list[dict[str, Any]] = []
        self._next_id = 1

    def log_activity(self, board_id, username, action, details=None):
        self._entries.append({
            "id": self._next_id,
            "board_id": board_id,
            "username": username,
            "action": action,
            "details": details,
            "created_at": "2026-01-15 10:30:00",
        })
        self._next_id += 1

    def list_activity(self, board_id, limit=50, offset=0):
        matching = [e for e in self._entries if e["board_id"] == board_id]
        matching.reverse()  # newest first
        return matching[offset:offset + limit]


class FakeActivityService:
    def __init__(self):
        self._entries: list[dict[str, Any]] = []
        self._next_id = 1

    def list_activity(self, board_id, limit=50, offset=0):
        matching = [e for e in self._entries if e["board_id"] == board_id]
        matching.reverse()
        return matching[offset:offset + limit]

    def log_activity(self, board_id, username, action, details=None):
        self._entries.append({
            "id": self._next_id,
            "board_id": board_id,
            "username": username,
            "action": action,
            "details": details,
            "created_at": "2026-01-15 10:30:00",
        })
        self._next_id += 1

    def diff_and_log(self, board_id, username, old_board, new_board):
        pass


class FakeBoardService:
    def __init__(self):
        self._boards: dict[int, dict[str, Any]] = {}
        self._next_id = 1

    def get_board(self, username, board_id=None):
        if board_id is not None:
            return self._boards.get(board_id)
        return None

    def list_boards(self, username):
        return []

    def create_board(self, username, name, template=None):
        board = default_board()
        bid = self._next_id
        self._next_id += 1
        board["id"] = bid
        board["name"] = name
        self._boards[bid] = board
        return board

    def save_board(self, username, board, board_id=None):
        if board_id is not None and board_id in self._boards:
            self._boards[board_id] = board
            return board
        return None

    def delete_board(self, username, board_id):
        return True

    def rename_board(self, username, board_id, name):
        return True


def _setup(monkeypatch):
    fake_activity = FakeActivityService()
    fake_board = FakeBoardService()
    monkeypatch.setattr(main_module, "activity_service", fake_activity)
    monkeypatch.setattr(main_module, "board_service", fake_board)

    board = fake_board.create_board("testuser", "Test Board")
    board_id = board["id"]

    client = TestClient(main_module.app)
    client.cookies.set(settings.auth_cookie_name, settings.sign_session("testuser"))
    return client, fake_activity, fake_board, board_id


# --- API endpoint tests ---

def test_list_activity_empty(monkeypatch):
    client, _, _, board_id = _setup(monkeypatch)
    resp = client.get(f"/api/boards/{board_id}/activity")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_activity_returns_logged_entries(monkeypatch):
    client, fake_activity, _, board_id = _setup(monkeypatch)
    fake_activity.log_activity(board_id, "testuser", "card_created", {"card_id": "c1"})
    fake_activity.log_activity(board_id, "testuser", "card_deleted", {"card_id": "c2"})
    resp = client.get(f"/api/boards/{board_id}/activity")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["action"] == "card_deleted"
    assert data[1]["action"] == "card_created"


def test_list_activity_pagination(monkeypatch):
    client, fake_activity, _, board_id = _setup(monkeypatch)
    for i in range(5):
        fake_activity.log_activity(board_id, "testuser", f"action_{i}")
    resp = client.get(f"/api/boards/{board_id}/activity?limit=2&offset=0")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp2 = client.get(f"/api/boards/{board_id}/activity?limit=2&offset=2")
    assert resp2.status_code == 200
    assert len(resp2.json()) == 2


def test_list_activity_requires_auth(monkeypatch):
    client, _, _, board_id = _setup(monkeypatch)
    client.cookies.clear()
    resp = client.get(f"/api/boards/{board_id}/activity")
    assert resp.status_code == 401


def test_list_activity_board_not_found(monkeypatch):
    client, _, _, _ = _setup(monkeypatch)
    resp = client.get("/api/boards/9999/activity")
    assert resp.status_code == 404


# --- diff_and_log unit tests ---

def test_diff_detects_card_created():
    repo = FakeActivityRepository()
    service = ActivityService(repository=repo)

    old_board = {
        "columns": [{"id": "col-1", "title": "Todo", "cardIds": []}],
        "cards": {},
    }
    new_board = {
        "columns": [{"id": "col-1", "title": "Todo", "cardIds": ["card-1"]}],
        "cards": {"card-1": {"id": "card-1", "title": "New task"}},
    }
    service.diff_and_log(1, "alice", old_board, new_board)
    assert len(repo._entries) == 1
    assert repo._entries[0]["action"] == "card_created"
    assert repo._entries[0]["details"]["card_id"] == "card-1"


def test_diff_detects_card_deleted():
    repo = FakeActivityRepository()
    service = ActivityService(repository=repo)

    old_board = {
        "columns": [{"id": "col-1", "title": "Todo", "cardIds": ["card-1"]}],
        "cards": {"card-1": {"id": "card-1", "title": "Old task"}},
    }
    new_board = {
        "columns": [{"id": "col-1", "title": "Todo", "cardIds": []}],
        "cards": {},
    }
    service.diff_and_log(1, "alice", old_board, new_board)
    assert len(repo._entries) == 1
    assert repo._entries[0]["action"] == "card_deleted"
    assert repo._entries[0]["details"]["title"] == "Old task"


def test_diff_detects_card_moved():
    repo = FakeActivityRepository()
    service = ActivityService(repository=repo)

    old_board = {
        "columns": [
            {"id": "col-1", "title": "Todo", "cardIds": ["card-1"]},
            {"id": "col-2", "title": "Done", "cardIds": []},
        ],
        "cards": {"card-1": {"id": "card-1", "title": "My task"}},
    }
    new_board = {
        "columns": [
            {"id": "col-1", "title": "Todo", "cardIds": []},
            {"id": "col-2", "title": "Done", "cardIds": ["card-1"]},
        ],
        "cards": {"card-1": {"id": "card-1", "title": "My task"}},
    }
    service.diff_and_log(1, "alice", old_board, new_board)
    assert len(repo._entries) == 1
    assert repo._entries[0]["action"] == "card_moved"
    assert repo._entries[0]["details"]["from_column"] == "Todo"
    assert repo._entries[0]["details"]["to_column"] == "Done"


def test_diff_detects_column_added():
    repo = FakeActivityRepository()
    service = ActivityService(repository=repo)

    old_board = {
        "columns": [{"id": "col-1", "title": "Todo", "cardIds": []}],
        "cards": {},
    }
    new_board = {
        "columns": [
            {"id": "col-1", "title": "Todo", "cardIds": []},
            {"id": "col-2", "title": "In Progress", "cardIds": []},
        ],
        "cards": {},
    }
    service.diff_and_log(1, "alice", old_board, new_board)
    assert len(repo._entries) == 1
    assert repo._entries[0]["action"] == "column_added"
    assert repo._entries[0]["details"]["title"] == "In Progress"


def test_diff_detects_column_deleted():
    repo = FakeActivityRepository()
    service = ActivityService(repository=repo)

    old_board = {
        "columns": [
            {"id": "col-1", "title": "Todo", "cardIds": []},
            {"id": "col-2", "title": "Done", "cardIds": []},
        ],
        "cards": {},
    }
    new_board = {
        "columns": [{"id": "col-1", "title": "Todo", "cardIds": []}],
        "cards": {},
    }
    service.diff_and_log(1, "alice", old_board, new_board)
    assert len(repo._entries) == 1
    assert repo._entries[0]["action"] == "column_deleted"
    assert repo._entries[0]["details"]["title"] == "Done"


def test_diff_no_changes_no_log():
    repo = FakeActivityRepository()
    service = ActivityService(repository=repo)

    board = {
        "columns": [{"id": "col-1", "title": "Todo", "cardIds": ["card-1"]}],
        "cards": {"card-1": {"id": "card-1", "title": "Task"}},
    }
    service.diff_and_log(1, "alice", board, board)
    assert len(repo._entries) == 0


def test_diff_multiple_changes():
    repo = FakeActivityRepository()
    service = ActivityService(repository=repo)

    old_board = {
        "columns": [
            {"id": "col-1", "title": "Todo", "cardIds": ["card-1"]},
        ],
        "cards": {"card-1": {"id": "card-1", "title": "Old"}},
    }
    new_board = {
        "columns": [
            {"id": "col-1", "title": "Todo", "cardIds": ["card-2"]},
            {"id": "col-new", "title": "Review", "cardIds": []},
        ],
        "cards": {"card-2": {"id": "card-2", "title": "New"}},
    }
    service.diff_and_log(1, "alice", old_board, new_board)
    actions = {e["action"] for e in repo._entries}
    assert "card_created" in actions
    assert "card_deleted" in actions
    assert "column_added" in actions
