"""Tests for card comments API endpoints."""
from typing import Any

from fastapi.testclient import TestClient

import app.main as main_module
from app.config import settings
from app.kanban import default_board


class FakeCommentService:
    def __init__(self):
        self._comments: list[dict[str, Any]] = []
        self._next_id = 1

    def list_comments(self, board_id, card_id, limit=50, offset=0):
        matching = [
            c for c in self._comments
            if c["board_id"] == board_id and c["card_id"] == card_id
        ]
        return matching[offset:offset + limit]

    def add_comment(self, board_id, card_id, username, content):
        comment = {
            "id": self._next_id,
            "board_id": board_id,
            "card_id": card_id,
            "username": username,
            "content": content,
            "created_at": "2026-01-15 10:30:00",
        }
        self._next_id += 1
        self._comments.append(comment)
        return {k: v for k, v in comment.items() if k != "board_id"}

    def delete_comment(self, comment_id, username):
        for i, c in enumerate(self._comments):
            if c["id"] == comment_id and c["username"] == username:
                self._comments.pop(i)
                return True
        return False

    def get_comment_counts(self, board_id):
        counts: dict[str, int] = {}
        for c in self._comments:
            if c["board_id"] == board_id:
                counts[c["card_id"]] = counts.get(c["card_id"], 0) + 1
        return counts


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
        return board

    def delete_board(self, username, board_id):
        return True

    def rename_board(self, username, board_id, name):
        return True


def _setup(monkeypatch):
    fake_comment = FakeCommentService()
    fake_board = FakeBoardService()
    monkeypatch.setattr(main_module, "comment_service", fake_comment)
    monkeypatch.setattr(main_module, "board_service", fake_board)

    # Create a board with cards
    board = fake_board.create_board("testuser", "Test Board")
    board_id = board["id"]

    client = TestClient(main_module.app)
    client.cookies.set(settings.auth_cookie_name, settings.sign_session("testuser"))
    return client, fake_comment, fake_board, board_id


def test_list_comments_empty(monkeypatch):
    client, _, _, board_id = _setup(monkeypatch)
    resp = client.get(f"/api/boards/{board_id}/cards/card-1/comments")
    assert resp.status_code == 200
    assert resp.json() == []


def test_add_comment(monkeypatch):
    client, _, _, board_id = _setup(monkeypatch)
    resp = client.post(
        f"/api/boards/{board_id}/cards/card-1/comments",
        json={"content": "This looks good!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "This looks good!"
    assert data["username"] == "testuser"
    assert data["card_id"] == "card-1"


def test_add_comment_then_list(monkeypatch):
    client, _, _, board_id = _setup(monkeypatch)
    client.post(
        f"/api/boards/{board_id}/cards/card-1/comments",
        json={"content": "First comment"},
    )
    client.post(
        f"/api/boards/{board_id}/cards/card-1/comments",
        json={"content": "Second comment"},
    )
    resp = client.get(f"/api/boards/{board_id}/cards/card-1/comments")
    assert resp.status_code == 200
    comments = resp.json()
    assert len(comments) == 2
    assert comments[0]["content"] == "First comment"
    assert comments[1]["content"] == "Second comment"


def test_add_comment_empty_content_rejected(monkeypatch):
    client, _, _, board_id = _setup(monkeypatch)
    resp = client.post(
        f"/api/boards/{board_id}/cards/card-1/comments",
        json={"content": ""},
    )
    assert resp.status_code == 422


def test_add_comment_board_not_found(monkeypatch):
    client, _, _, _ = _setup(monkeypatch)
    resp = client.post(
        "/api/boards/9999/cards/card-1/comments",
        json={"content": "Hello"},
    )
    assert resp.status_code == 404


def test_add_comment_card_not_found(monkeypatch):
    client, _, _, board_id = _setup(monkeypatch)
    resp = client.post(
        f"/api/boards/{board_id}/cards/nonexistent/comments",
        json={"content": "Hello"},
    )
    assert resp.status_code == 404


def test_delete_own_comment(monkeypatch):
    client, _, _, board_id = _setup(monkeypatch)
    resp = client.post(
        f"/api/boards/{board_id}/cards/card-1/comments",
        json={"content": "To delete"},
    )
    comment_id = resp.json()["id"]
    resp = client.delete(
        f"/api/boards/{board_id}/cards/card-1/comments/{comment_id}",
    )
    assert resp.status_code == 204


def test_delete_nonexistent_comment(monkeypatch):
    client, _, _, board_id = _setup(monkeypatch)
    resp = client.delete(
        f"/api/boards/{board_id}/cards/card-1/comments/9999",
    )
    assert resp.status_code == 404


def test_list_comments_requires_auth(monkeypatch):
    client, _, _, board_id = _setup(monkeypatch)
    client.cookies.clear()
    resp = client.get(f"/api/boards/{board_id}/cards/card-1/comments")
    assert resp.status_code == 401


def test_add_comment_requires_auth(monkeypatch):
    client, _, _, board_id = _setup(monkeypatch)
    client.cookies.clear()
    resp = client.post(
        f"/api/boards/{board_id}/cards/card-1/comments",
        json={"content": "Hello"},
    )
    assert resp.status_code == 401
