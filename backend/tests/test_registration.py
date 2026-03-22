from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

import app.main as main_module
from app.config import settings


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


def test_register_creates_new_user(monkeypatch) -> None:
    fake_repo = FakeUserRepository()
    monkeypatch.setattr(main_module, "user_repository", fake_repo)

    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/auth/register",
            json={"username": "newuser", "password": "securepassword"},
        )

    assert response.status_code == 201
    assert response.json() == {"authenticated": True, "username": "newuser"}
    assert "newuser" in fake_repo.users


def test_register_rejects_duplicate_username(monkeypatch) -> None:
    fake_repo = FakeUserRepository()
    fake_repo.create_user("existing", "password123")
    monkeypatch.setattr(main_module, "user_repository", fake_repo)

    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/auth/register",
            json={"username": "existing", "password": "password123"},
        )

    assert response.status_code == 409
    assert response.json() == {"detail": "Username already taken."}


def test_register_rejects_short_password(monkeypatch) -> None:
    fake_repo = FakeUserRepository()
    monkeypatch.setattr(main_module, "user_repository", fake_repo)

    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/auth/register",
            json={"username": "newuser", "password": "short"},
        )

    assert response.status_code == 422


def test_register_rejects_short_username(monkeypatch) -> None:
    fake_repo = FakeUserRepository()
    monkeypatch.setattr(main_module, "user_repository", fake_repo)

    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/auth/register",
            json={"username": "x", "password": "securepassword"},
        )

    assert response.status_code == 422


def test_register_sets_session_cookie(monkeypatch) -> None:
    fake_repo = FakeUserRepository()
    monkeypatch.setattr(main_module, "user_repository", fake_repo)

    with TestClient(main_module.app) as client:
        client.post(
            "/api/auth/register",
            json={"username": "newuser", "password": "securepassword"},
        )
        session_response = client.get("/api/auth/session")

    assert session_response.status_code == 200
    assert session_response.json()["authenticated"] is True
    assert session_response.json()["username"] == "newuser"


def test_login_with_db_backed_user(monkeypatch) -> None:
    fake_repo = FakeUserRepository()
    fake_repo.create_user("dbuser", "mypassword")
    monkeypatch.setattr(main_module, "user_repository", fake_repo)

    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/auth/login",
            json={"username": "dbuser", "password": "mypassword"},
        )

    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "username": "dbuser"}


def test_login_with_db_backed_user_wrong_password(monkeypatch) -> None:
    fake_repo = FakeUserRepository()
    fake_repo.create_user("dbuser", "mypassword")
    monkeypatch.setattr(main_module, "user_repository", fake_repo)

    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/auth/login",
            json={"username": "dbuser", "password": "wrongpassword"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials."}
