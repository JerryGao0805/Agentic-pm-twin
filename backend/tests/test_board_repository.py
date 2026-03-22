import json
from contextlib import contextmanager
from typing import Any

import app.repositories.board_repository as repository_module
from app.kanban import default_board
from app.repositories.board_repository import BoardRepository


class RecordingCursor:
    def __init__(self, fetch_values: list[Any] | None = None) -> None:
        self.statements: list[tuple[str, Any]] = []
        self._fetch_values = fetch_values or []
        self._fetch_index = 0

    def execute(self, statement: str, params: Any = None) -> None:
        self.statements.append((" ".join(statement.split()), params))

    def fetchone(self) -> Any:
        if self._fetch_index < len(self._fetch_values):
            value = self._fetch_values[self._fetch_index]
            self._fetch_index += 1
            return value
        return None

    def fetchall(self) -> list[Any]:
        remaining = self._fetch_values[self._fetch_index:]
        self._fetch_index = len(self._fetch_values)
        return remaining

    @property
    def lastrowid(self) -> int:
        return 42

    @property
    def rowcount(self) -> int:
        return 1

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
    monkeypatch.setattr(repository_module, "ensure_user_id", lambda _cursor, _username: 21)


def test_get_board_returns_existing_payload(monkeypatch) -> None:
    board = default_board()
    cursor = RecordingCursor(fetch_values=[(1, "My Board", json.dumps(board))])
    connection = RecordingConnection(cursor)
    _patch_db(monkeypatch, cursor, connection)

    repository = BoardRepository()
    loaded = repository.get_board("user")

    expected = board.copy()
    expected["id"] = 1
    expected["name"] = "My Board"
    assert loaded == expected


def test_get_board_seeds_default_board_when_missing(monkeypatch) -> None:
    cursor = RecordingCursor(fetch_values=[None])
    connection = RecordingConnection(cursor)
    _patch_db(monkeypatch, cursor, connection)

    repository = BoardRepository()
    loaded = repository.get_board("user")

    expected = default_board()
    expected["id"] = 42
    expected["name"] = "My Board"
    assert loaded == expected
    assert any("INSERT INTO boards" in statement for statement, _ in cursor.statements)


def test_save_board_uses_update_when_board_id_provided(monkeypatch) -> None:
    board = default_board()
    cursor = RecordingCursor()
    connection = RecordingConnection(cursor)
    _patch_db(monkeypatch, cursor, connection)

    repository = BoardRepository()
    repository.save_board("user", board, board_id=5)

    assert any("UPDATE boards SET" in statement for statement, _ in cursor.statements)
    assert connection.commit_count == 1


def test_list_boards(monkeypatch) -> None:
    cursor = RecordingCursor(fetch_values=[
        (1, "Board A", "2026-01-01"),
        (2, "Board B", "2026-01-02"),
    ])
    connection = RecordingConnection(cursor)
    _patch_db(monkeypatch, cursor, connection)

    repository = BoardRepository()
    boards = repository.list_boards("user")

    assert len(boards) == 2
    assert boards[0]["name"] == "Board A"
    assert boards[1]["name"] == "Board B"


def test_create_board(monkeypatch) -> None:
    cursor = RecordingCursor()
    connection = RecordingConnection(cursor)
    _patch_db(monkeypatch, cursor, connection)

    repository = BoardRepository()
    board = repository.create_board("user", "Sprint Board")

    assert board["id"] == 42
    assert board["name"] == "Sprint Board"
    assert any("INSERT INTO boards" in statement for statement, _ in cursor.statements)


def test_delete_board(monkeypatch) -> None:
    cursor = RecordingCursor()
    connection = RecordingConnection(cursor)
    _patch_db(monkeypatch, cursor, connection)

    repository = BoardRepository()
    result = repository.delete_board("user", 5)

    assert result is True
    assert any("DELETE FROM boards" in statement for statement, _ in cursor.statements)


def test_rename_board(monkeypatch) -> None:
    cursor = RecordingCursor()
    connection = RecordingConnection(cursor)
    _patch_db(monkeypatch, cursor, connection)

    repository = BoardRepository()
    result = repository.rename_board("user", 5, "New Name")

    assert result is True
    assert any("UPDATE boards SET name" in statement for statement, _ in cursor.statements)
