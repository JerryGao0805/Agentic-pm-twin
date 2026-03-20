from typing import Any

import pytest
from pydantic import ValidationError

from app.kanban import default_board
from app.services.board_service import BoardService


class FakeBoardRepository:
    def __init__(self) -> None:
        self.saved_by_username: dict[str, dict[str, Any]] = {}
        self._boards: dict[int, dict[str, Any]] = {}
        self._next_id = 1

    def list_boards(self, username: str) -> list[dict[str, Any]]:
        return [
            {"id": bid, "name": b.get("name", "Board"), "updated_at": "2026-01-01"}
            for bid, b in self._boards.items()
        ]

    def get_board(self, username: str, board_id: int | None = None) -> dict[str, Any]:
        if board_id and board_id in self._boards:
            return self._boards[board_id]
        return self.saved_by_username.get(username, default_board())

    def create_board(self, username: str, name: str) -> dict[str, Any]:
        board = default_board()
        bid = self._next_id
        self._next_id += 1
        board["id"] = bid
        board["name"] = name
        self._boards[bid] = board
        return board

    def save_board(self, username: str, board: dict[str, Any], board_id: int | None = None) -> bool:
        self.saved_by_username[username] = board
        return True

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


def test_get_board_validates_repository_data() -> None:
    repository = FakeBoardRepository()
    service = BoardService(repository=repository)

    board = service.get_board("user")

    assert board["columns"][0]["id"] == "col-backlog"
    assert board["cards"]["card-1"]["title"] == "Align roadmap themes"


def test_save_board_rejects_invalid_payload() -> None:
    repository = FakeBoardRepository()
    service = BoardService(repository=repository)
    invalid_board = {"columns": [], "cards": {}}

    with pytest.raises(ValidationError):
        service.save_board("user", invalid_board)


def test_save_board_persists_valid_board() -> None:
    repository = FakeBoardRepository()
    service = BoardService(repository=repository)
    board = default_board()
    board["columns"][0]["title"] = "Ideas"

    saved = service.save_board("user", board)

    assert saved["columns"][0]["title"] == "Ideas"
    assert repository.saved_by_username["user"]["columns"][0]["title"] == "Ideas"


def test_create_board() -> None:
    repository = FakeBoardRepository()
    service = BoardService(repository=repository)

    board = service.create_board("user", "Sprint Board")

    assert board["name"] == "Sprint Board"
    assert "id" in board


def test_list_boards() -> None:
    repository = FakeBoardRepository()
    service = BoardService(repository=repository)

    repository.create_board("user", "Board A")
    repository.create_board("user", "Board B")

    boards = service.list_boards("user")
    assert len(boards) == 2


def test_delete_board() -> None:
    repository = FakeBoardRepository()
    service = BoardService(repository=repository)

    repository.create_board("user", "To Delete")

    assert service.delete_board("user", 1) is True
    assert service.delete_board("user", 999) is False


def test_rename_board() -> None:
    repository = FakeBoardRepository()
    service = BoardService(repository=repository)

    repository.create_board("user", "Old Name")

    assert service.rename_board("user", 1, "New Name") is True
    assert repository._boards[1]["name"] == "New Name"


def test_save_board_with_custom_columns() -> None:
    repository = FakeBoardRepository()
    service = BoardService(repository=repository)

    board = {
        "columns": [
            {"id": "col-todo", "title": "To Do", "cardIds": ["c1"]},
            {"id": "col-done", "title": "Done", "cardIds": []},
        ],
        "cards": {
            "c1": {"id": "c1", "title": "A task", "details": ""},
        },
    }

    saved = service.save_board("user", board)
    assert len(saved["columns"]) == 2
    assert saved["columns"][0]["id"] == "col-todo"


def test_save_board_with_card_enhancements() -> None:
    repository = FakeBoardRepository()
    service = BoardService(repository=repository)

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
                "assignee": "alice",
            },
        },
    }

    saved = service.save_board("user", board)
    assert saved["cards"]["c1"]["priority"] == "high"
    assert saved["cards"]["c1"]["due_date"] == "2026-04-01"
    assert saved["cards"]["c1"]["assignee"] == "alice"
