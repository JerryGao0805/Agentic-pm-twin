from __future__ import annotations

import json
from typing import Any

from app.db import db_connection, ensure_user_id
from app.kanban import default_board


class BoardRepository:
    def list_boards(self, username: str) -> list[dict[str, Any]]:
        with db_connection() as (connection, cursor):
            user_id = ensure_user_id(cursor, username)
            cursor.execute(
                "SELECT id, name, updated_at FROM boards WHERE user_id = %s ORDER BY updated_at DESC",
                (user_id,),
            )
            rows = cursor.fetchall()
            return [
                {"id": int(row[0]), "name": str(row[1]), "updated_at": str(row[2])}
                for row in rows
            ]

    def get_board(self, username: str, board_id: int | None = None) -> dict[str, Any] | None:
        with db_connection() as (connection, cursor):
            user_id = ensure_user_id(cursor, username)

            if board_id is not None:
                cursor.execute(
                    "SELECT id, name, board_json FROM boards WHERE id = %s AND user_id = %s",
                    (board_id, user_id),
                )
            else:
                cursor.execute(
                    "SELECT id, name, board_json FROM boards WHERE user_id = %s ORDER BY updated_at DESC LIMIT 1",
                    (user_id,),
                )
            row = cursor.fetchone()

            if row is None:
                if board_id is not None:
                    return None
                board = default_board()
                cursor.execute(
                    """
                    INSERT INTO boards (user_id, name, board_json)
                    VALUES (%s, %s, CAST(%s AS JSON))
                    """,
                    (user_id, "My Board", json.dumps(board)),
                )
                new_board_id = int(cursor.lastrowid)
                board["id"] = new_board_id
                board["name"] = "My Board"
                return board

            board_data = self._decode_board_json(row[2])
            board_data["id"] = int(row[0])
            board_data["name"] = str(row[1])
            return board_data

    def create_board(self, username: str, name: str, initial_board: dict[str, Any] | None = None) -> dict[str, Any]:
        with db_connection() as (connection, cursor):
            user_id = ensure_user_id(cursor, username)
            board = initial_board if initial_board is not None else default_board()
            cursor.execute(
                """
                INSERT INTO boards (user_id, name, board_json)
                VALUES (%s, %s, CAST(%s AS JSON))
                """,
                (user_id, name, json.dumps(board)),
            )
            new_board_id = int(cursor.lastrowid)
            board["id"] = new_board_id
            board["name"] = name
            return board

    def save_board(self, username: str, board: dict[str, Any], board_id: int | None = None) -> bool:
        board_copy = {k: v for k, v in board.items() if k not in ("id", "name")}
        serialized_board = json.dumps(board_copy)
        board_name = board.get("name")
        with db_connection() as (connection, cursor):
            user_id = ensure_user_id(cursor, username)

            if board_id is not None:
                if board_name is not None:
                    cursor.execute(
                        "UPDATE boards SET board_json = CAST(%s AS JSON), name = %s WHERE id = %s AND user_id = %s",
                        (serialized_board, board_name, board_id, user_id),
                    )
                else:
                    cursor.execute(
                        "UPDATE boards SET board_json = CAST(%s AS JSON) WHERE id = %s AND user_id = %s",
                        (serialized_board, board_id, user_id),
                    )
                return cursor.rowcount > 0
            else:
                cursor.execute(
                    """
                    INSERT INTO boards (user_id, name, board_json)
                    VALUES (%s, %s, CAST(%s AS JSON))
                    """,
                    (user_id, board_name or "My Board", serialized_board),
                )
            return True

    def delete_board(self, username: str, board_id: int) -> bool:
        with db_connection() as (connection, cursor):
            user_id = ensure_user_id(cursor, username)
            cursor.execute(
                "DELETE FROM boards WHERE id = %s AND user_id = %s",
                (board_id, user_id),
            )
            return cursor.rowcount > 0

    def rename_board(self, username: str, board_id: int, name: str) -> bool:
        with db_connection() as (connection, cursor):
            user_id = ensure_user_id(cursor, username)
            cursor.execute(
                "UPDATE boards SET name = %s WHERE id = %s AND user_id = %s",
                (name, board_id, user_id),
            )
            return cursor.rowcount > 0

    @staticmethod
    def _decode_board_json(raw_value: Any) -> dict[str, Any]:
        if isinstance(raw_value, dict):
            return raw_value
        if isinstance(raw_value, (bytes, bytearray)):
            return json.loads(raw_value.decode("utf-8"))
        if isinstance(raw_value, str):
            return json.loads(raw_value)
        raise ValueError("Unexpected board_json value type.")
