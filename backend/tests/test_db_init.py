from typing import Any

from mysql.connector import Error

import app.db as db_module


class RecordingCursor:
    def __init__(self, fetch_values: list[Any] | None = None) -> None:
        self.statements: list[tuple[str, Any]] = []
        self._fetch_values = fetch_values or []
        self._fetch_index = 0

    def execute(self, statement: str, params: Any = None) -> None:
        normalized = " ".join(statement.split())
        self.statements.append((normalized, params))

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


def test_create_database_falls_back_to_admin_credentials(monkeypatch) -> None:
    cursor = RecordingCursor()
    connection = RecordingConnection(cursor)
    calls: list[tuple[str | None, bool]] = []

    def fake_connect(*, database: str | None, use_admin_credentials: bool):
        calls.append((database, use_admin_credentials))
        if not use_admin_credentials:
            raise Error("permission denied")
        return connection

    monkeypatch.setattr(db_module, "_connect", fake_connect)

    db_module._create_database_if_missing()

    assert calls == [(None, False), (None, True)]
    assert any(
        "CREATE DATABASE IF NOT EXISTS" in statement
        for statement, _ in cursor.statements
    )


def test_initialize_database_creates_schema_and_seeds_default_board(monkeypatch) -> None:
    # Return values: ensure_user_id returns 17
    # Then SELECT password_hash returns (None,) meaning no password set
    # Then UPDATE password_hash completes
    # Then SELECT 1 FROM boards returns None (no board exists)
    # Then INSERT INTO boards completes
    cursor = RecordingCursor(fetch_values=[(None,), None])
    connection = RecordingConnection(cursor)

    monkeypatch.setattr(db_module, "_create_database_if_missing", lambda: None)
    monkeypatch.setattr(db_module, "get_connection", lambda database=None: connection)
    monkeypatch.setattr(db_module, "ensure_user_id", lambda _cursor, _username: 17)

    db_module.initialize_database()

    executed_statements = [statement for statement, _ in cursor.statements]

    assert any("CREATE TABLE IF NOT EXISTS users" in statement for statement in executed_statements)
    assert any("CREATE TABLE IF NOT EXISTS boards" in statement for statement in executed_statements)
    assert any(
        "CREATE TABLE IF NOT EXISTS chat_messages" in statement
        for statement in executed_statements
    )
    assert any(
        "INSERT INTO boards" in statement
        for statement in executed_statements
    )
    assert connection.commit_count == 1
