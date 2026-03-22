"""Tests for user profile management endpoints."""
from typing import Any

from fastapi.testclient import TestClient

import app.main as main_module
from app.config import settings


class FakeUserRepository:
    def __init__(self):
        self.users: dict[str, dict[str, Any]] = {}
        self._next_id = 1

    def create_user(self, username: str, password: str) -> int:
        user_id = self._next_id
        self._next_id += 1
        self.users[username] = {
            "id": user_id,
            "username": username,
            "password_hash": f"hashed_{password}",
            "created_at": "2026-01-15 10:30:00",
        }
        return user_id

    def get_user_by_username(self, username: str) -> dict | None:
        return self.users.get(username)

    def verify_password(self, password: str, password_hash: str) -> bool:
        return password_hash == f"hashed_{password}"

    def get_profile(self, username: str) -> dict | None:
        user = self.users.get(username)
        if user is None:
            return None
        return {
            "id": user["id"],
            "username": user["username"],
            "created_at": user["created_at"],
            "board_count": user.get("board_count", 0),
        }

    def update_password(self, username: str, new_password: str) -> bool:
        if username not in self.users:
            return False
        self.users[username]["password_hash"] = f"hashed_{new_password}"
        return True

    def delete_user(self, username: str) -> bool:
        return self.users.pop(username, None) is not None


def _setup(monkeypatch) -> tuple[TestClient, FakeUserRepository]:
    fake_repo = FakeUserRepository()
    monkeypatch.setattr(main_module, "user_repository", fake_repo)

    fake_repo.create_user("alice", "secret123")
    fake_repo.users["alice"]["board_count"] = 3

    client = TestClient(main_module.app)
    client.cookies.set(
        settings.auth_cookie_name,
        settings.sign_session("alice"),
    )
    return client, fake_repo


def test_get_profile(monkeypatch):
    client, _ = _setup(monkeypatch)
    resp = client.get("/api/auth/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "alice"
    assert data["board_count"] == 3
    assert "created_at" in data


def test_get_profile_requires_auth(monkeypatch):
    client, _ = _setup(monkeypatch)
    client.cookies.clear()
    resp = client.get("/api/auth/profile")
    assert resp.status_code == 401


def test_change_password_success(monkeypatch):
    client, fake_repo = _setup(monkeypatch)
    resp = client.patch(
        "/api/auth/password",
        json={"current_password": "secret123", "new_password": "newsecret456"},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Password updated."
    assert fake_repo.users["alice"]["password_hash"] == "hashed_newsecret456"


def test_change_password_wrong_current(monkeypatch):
    client, _ = _setup(monkeypatch)
    resp = client.patch(
        "/api/auth/password",
        json={"current_password": "wrongpassword", "new_password": "newsecret456"},
    )
    assert resp.status_code == 401
    assert "incorrect" in resp.json()["detail"].lower()


def test_change_password_too_short(monkeypatch):
    client, _ = _setup(monkeypatch)
    resp = client.patch(
        "/api/auth/password",
        json={"current_password": "secret123", "new_password": "ab"},
    )
    assert resp.status_code == 422


def test_change_password_requires_auth(monkeypatch):
    client, _ = _setup(monkeypatch)
    client.cookies.clear()
    resp = client.patch(
        "/api/auth/password",
        json={"current_password": "secret123", "new_password": "newsecret456"},
    )
    assert resp.status_code == 401


def test_delete_account(monkeypatch):
    client, fake_repo = _setup(monkeypatch)
    resp = client.delete("/api/auth/account")
    assert resp.status_code == 204
    assert "alice" not in fake_repo.users


def test_delete_account_requires_auth(monkeypatch):
    client, _ = _setup(monkeypatch)
    client.cookies.clear()
    resp = client.delete("/api/auth/account")
    assert resp.status_code == 401
