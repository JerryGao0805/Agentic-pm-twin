from __future__ import annotations

from typing import Any

from app.repositories.activity_repository import ActivityRepository


class ActivityService:
    def __init__(self, repository: ActivityRepository | None = None) -> None:
        self._repository = repository or ActivityRepository()

    def list_activity(
        self, board_id: int, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        return self._repository.list_activity(board_id, limit=limit, offset=offset)

    def log_activity(
        self, board_id: int, username: str, action: str, details: dict[str, Any] | None = None
    ) -> None:
        self._repository.log_activity(board_id, username, action, details)

    def diff_and_log(
        self, board_id: int, username: str, old_board: dict[str, Any], new_board: dict[str, Any]
    ) -> None:
        old_cards = set(old_board.get("cards", {}).keys())
        new_cards = set(new_board.get("cards", {}).keys())

        for card_id in new_cards - old_cards:
            card = new_board["cards"][card_id]
            self._repository.log_activity(
                board_id, username, "card_created",
                {"card_id": card_id, "title": card.get("title", "")},
            )

        for card_id in old_cards - new_cards:
            card = old_board["cards"][card_id]
            self._repository.log_activity(
                board_id, username, "card_deleted",
                {"card_id": card_id, "title": card.get("title", "")},
            )

        old_columns = {c["id"]: c for c in old_board.get("columns", [])}
        new_columns = {c["id"]: c for c in new_board.get("columns", [])}

        for col_id in set(new_columns) - set(old_columns):
            self._repository.log_activity(
                board_id, username, "column_added",
                {"column_id": col_id, "title": new_columns[col_id].get("title", "")},
            )

        for col_id in set(old_columns) - set(new_columns):
            self._repository.log_activity(
                board_id, username, "column_deleted",
                {"column_id": col_id, "title": old_columns[col_id].get("title", "")},
            )

        # Detect card moves between columns
        old_card_col: dict[str, str] = {}
        for col in old_board.get("columns", []):
            for cid in col.get("cardIds", []):
                old_card_col[cid] = col["id"]

        new_card_col: dict[str, str] = {}
        for col in new_board.get("columns", []):
            for cid in col.get("cardIds", []):
                new_card_col[cid] = col["id"]

        for card_id in old_cards & new_cards:
            old_col = old_card_col.get(card_id)
            new_col = new_card_col.get(card_id)
            if old_col and new_col and old_col != new_col:
                self._repository.log_activity(
                    board_id, username, "card_moved",
                    {
                        "card_id": card_id,
                        "title": new_board["cards"][card_id].get("title", ""),
                        "from_column": old_columns.get(old_col, {}).get("title", old_col),
                        "to_column": new_columns.get(new_col, {}).get("title", new_col),
                    },
                )
