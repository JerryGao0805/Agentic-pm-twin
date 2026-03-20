from typing import Any

import app.repositories.chat_repository as repository_module
from app.repositories.chat_repository import ChatRepository


class RecordingCursor:
    def __init__(self, fetchall_values: list[Any] | None = None) -> None:
        self.statements: list[tuple[str, Any]] = []
        self._fetchall_values = fetchall_values or []

    def execute(self, statement: str, params: Any = None) -> None:
        self.statements.append((" ".join(statement.split()), params))

    def fetchall(self) -> list[Any]:
        return self._fetchall_values

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


def test_list_messages_returns_chat_rows(monkeypatch) -> None:
    cursor = RecordingCursor(fetchall_values=[("user", "hello"), ("assistant", "hi")])
    connection = RecordingConnection(cursor)

    monkeypatch.setattr(repository_module, "get_connection", lambda database=None: connection)
    monkeypatch.setattr(repository_module, "ensure_user_id", lambda _cursor, _username: 42)

    repository = ChatRepository()
    messages = repository.list_messages("user")

    assert messages == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    assert any("SELECT role, content" in statement for statement, _ in cursor.statements)
    assert connection.commit_count == 1


def test_list_messages_with_board_id(monkeypatch) -> None:
    cursor = RecordingCursor(fetchall_values=[("user", "board msg")])
    connection = RecordingConnection(cursor)

    monkeypatch.setattr(repository_module, "get_connection", lambda database=None: connection)
    monkeypatch.setattr(repository_module, "ensure_user_id", lambda _cursor, _username: 42)

    repository = ChatRepository()
    messages = repository.list_messages("user", board_id=5)

    assert messages == [{"role": "user", "content": "board msg"}]
    assert any("board_id" in statement for statement, _ in cursor.statements)


def test_append_message_inserts_chat_row(monkeypatch) -> None:
    cursor = RecordingCursor()
    connection = RecordingConnection(cursor)

    monkeypatch.setattr(repository_module, "get_connection", lambda database=None: connection)
    monkeypatch.setattr(repository_module, "ensure_user_id", lambda _cursor, _username: 42)

    repository = ChatRepository()
    repository.append_message("user", "assistant", "done")

    assert any(
        "INSERT INTO chat_messages" in statement
        for statement, _ in cursor.statements
    )
    assert any(
        params == (42, None, "assistant", "done")
        for _, params in cursor.statements
    )
    assert connection.commit_count == 1


def test_append_message_with_board_id(monkeypatch) -> None:
    cursor = RecordingCursor()
    connection = RecordingConnection(cursor)

    monkeypatch.setattr(repository_module, "get_connection", lambda database=None: connection)
    monkeypatch.setattr(repository_module, "ensure_user_id", lambda _cursor, _username: 42)

    repository = ChatRepository()
    repository.append_message("user", "user", "hello", board_id=7)

    assert any(
        params == (42, 7, "user", "hello")
        for _, params in cursor.statements
    )
