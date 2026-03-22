from contextlib import contextmanager
from typing import Any

import app.repositories.user_repository as repository_module
from app.repositories.user_repository import UserRepository


class RecordingCursor:
    def __init__(self, fetch_values: list[Any] | None = None) -> None:
        self.statements: list[tuple[str, Any]] = []
        self._fetch_values = fetch_values or []
        self._fetch_index = 0
        self.lastrowid = 42

    def execute(self, statement: str, params: Any = None) -> None:
        self.statements.append((" ".join(statement.split()), params))

    def fetchone(self) -> Any:
        if self._fetch_index < len(self._fetch_values):
            value = self._fetch_values[self._fetch_index]
            self._fetch_index += 1
            return value
        return None

    def close(self) -> None:
        return None


class RecordingConnection:
    def __init__(self, cursor: RecordingCursor) -> None:
        self._cursor = cursor
        self.commit_count = 0

    def cursor(self) -> RecordingCursor:
        return self._cursor

    def commit(self) -> None:
        self.commit_count += 1

    def close(self) -> None:
        return None


def _patch_db(monkeypatch, cursor, connection):
    @contextmanager
    def fake_db_connection(*, commit=True):
        yield connection, cursor
        if commit:
            connection.commit()
    monkeypatch.setattr(repository_module, "db_connection", fake_db_connection)


def test_create_user_inserts_with_hashed_password(monkeypatch) -> None:
    cursor = RecordingCursor()
    connection = RecordingConnection(cursor)
    _patch_db(monkeypatch, cursor, connection)

    repo = UserRepository()
    user_id = repo.create_user("alice", "secret123")

    assert user_id == 42
    assert any("INSERT INTO users" in stmt for stmt, _ in cursor.statements)
    # Verify bcrypt hash was passed (not plaintext)
    insert_stmt = next(
        (stmt, params) for stmt, params in cursor.statements if "INSERT INTO users" in stmt
    )
    assert insert_stmt[1][0] == "alice"
    assert insert_stmt[1][1].startswith("$2b$")  # bcrypt hash prefix
    assert connection.commit_count == 1


def test_get_user_by_username_returns_user(monkeypatch) -> None:
    cursor = RecordingCursor(fetch_values=[(10, "bob", "$2b$12$hash")])
    connection = RecordingConnection(cursor)
    _patch_db(monkeypatch, cursor, connection)

    repo = UserRepository()
    user = repo.get_user_by_username("bob")

    assert user is not None
    assert user["id"] == 10
    assert user["username"] == "bob"
    assert user["password_hash"] == "$2b$12$hash"


def test_get_user_by_username_returns_none_for_missing(monkeypatch) -> None:
    cursor = RecordingCursor(fetch_values=[])
    connection = RecordingConnection(cursor)
    _patch_db(monkeypatch, cursor, connection)

    repo = UserRepository()
    user = repo.get_user_by_username("nonexistent")

    assert user is None


def test_verify_password_correct() -> None:
    import bcrypt
    password = "testpassword"
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    repo = UserRepository()
    assert repo.verify_password(password, hashed) is True


def test_verify_password_incorrect() -> None:
    import bcrypt
    hashed = bcrypt.hashpw(b"correct", bcrypt.gensalt()).decode()

    repo = UserRepository()
    assert repo.verify_password("wrong", hashed) is False
