from __future__ import annotations

from typing import Any

from app.kanban import BoardPayload
from app.repositories.board_repository import BoardRepository


class BoardService:
    def __init__(self, repository: BoardRepository | None = None) -> None:
        self._repository = repository or BoardRepository()

    def list_boards(self, username: str) -> list[dict[str, Any]]:
        return self._repository.list_boards(username)

    def get_board(self, username: str, board_id: int | None = None) -> dict[str, Any] | None:
        board = self._repository.get_board(username, board_id=board_id)
        if board is None:
            return None
        board_meta = {k: v for k, v in board.items() if k in ("id", "name")}
        board_data = {k: v for k, v in board.items() if k not in ("id", "name")}
        validated_board = BoardPayload.model_validate(board_data)
        result = validated_board.model_dump()
        result.update(board_meta)
        return result

    def create_board(self, username: str, name: str) -> dict[str, Any]:
        board = self._repository.create_board(username, name)
        board_meta = {k: v for k, v in board.items() if k in ("id", "name")}
        board_data = {k: v for k, v in board.items() if k not in ("id", "name")}
        validated_board = BoardPayload.model_validate(board_data)
        result = validated_board.model_dump()
        result.update(board_meta)
        return result

    def save_board(
        self,
        username: str,
        board: BoardPayload | dict[str, Any],
        board_id: int | None = None,
    ) -> dict[str, Any] | None:
        if isinstance(board, dict):
            board_meta = {k: v for k, v in board.items() if k in ("id", "name")}
            board_data = {k: v for k, v in board.items() if k not in ("id", "name")}
            validated_board = BoardPayload.model_validate(board_data)
            board_payload = validated_board.model_dump()
            board_payload.update(board_meta)
        else:
            validated_board = board
            board_payload = validated_board.model_dump()

        effective_board_id = board_id or board_payload.get("id")
        saved = self._repository.save_board(username, board_payload, board_id=effective_board_id)
        if not saved:
            return None
        return board_payload

    def delete_board(self, username: str, board_id: int) -> bool:
        return self._repository.delete_board(username, board_id)

    def rename_board(self, username: str, board_id: int, name: str) -> bool:
        return self._repository.rename_board(username, board_id, name)
