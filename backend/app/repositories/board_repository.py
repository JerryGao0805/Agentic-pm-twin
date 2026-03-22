from __future__ import annotations

import json
from typing import Any

from app.config import settings
from app.db import ensure_user_id, get_connection
from app.kanban import default_board


class BoardRepository:
    def list_boards(self, username: str) -> list[dict[str, Any]]:
        connection = None
        cursor = None
        try:
            connection = get_connection(database=settings.db_name)
            cursor = connection.cursor()
            user_id = ensure_user_id(cursor, username)
            cursor.execute(
                "SELECT id, name, updated_at FROM boards WHERE user_id = %s ORDER BY updated_at DESC",
                (user_id,),
            )
            rows = cursor.fetchall()
            connection.commit()
            return [
                {"id": int(row[0]), "name": str(row[1]), "updated_at": str(row[2])}
                for row in rows
            ]
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()

    def get_board(self, username: str, board_id: int | None = None) -> dict[str, Any] | None:
        connection = None
        cursor = None
        try:
            connection = get_connection(database=settings.db_name)
            cursor = connection.cursor()

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
                    connection.commit()
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
                connection.commit()
                board["id"] = new_board_id
                board["name"] = "My Board"
                return board

            connection.commit()
            board_data = self._decode_board_json(row[2])
            board_data["id"] = int(row[0])
            board_data["name"] = str(row[1])
            return board_data
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()

    def create_board(self, username: str, name: str, initial_board: dict[str, Any] | None = None) -> dict[str, Any]:
        connection = None
        cursor = None
        try:
            connection = get_connection(database=settings.db_name)
            cursor = connection.cursor()
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
            connection.commit()
            board["id"] = new_board_id
            board["name"] = name
            return board
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()

    def save_board(self, username: str, board: dict[str, Any], board_id: int | None = None) -> bool:
        connection = None
        cursor = None
        board_copy = {k: v for k, v in board.items() if k not in ("id", "name")}
        serialized_board = json.dumps(board_copy)
        board_name = board.get("name")
        try:
            connection = get_connection(database=settings.db_name)
            cursor = connection.cursor()

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
                updated = cursor.rowcount > 0
                connection.commit()
                return updated
            else:
                cursor.execute(
                    """
                    INSERT INTO boards (user_id, name, board_json)
                    VALUES (%s, %s, CAST(%s AS JSON))
                    """,
                    (user_id, board_name or "My Board", serialized_board),
                )
            connection.commit()
            return True
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()

    def delete_board(self, username: str, board_id: int) -> bool:
        connection = None
        cursor = None
        try:
            connection = get_connection(database=settings.db_name)
            cursor = connection.cursor()
            user_id = ensure_user_id(cursor, username)
            cursor.execute(
                "DELETE FROM boards WHERE id = %s AND user_id = %s",
                (board_id, user_id),
            )
            deleted = cursor.rowcount > 0
            connection.commit()
            return deleted
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()

    def rename_board(self, username: str, board_id: int, name: str) -> bool:
        connection = None
        cursor = None
        try:
            connection = get_connection(database=settings.db_name)
            cursor = connection.cursor()
            user_id = ensure_user_id(cursor, username)
            cursor.execute(
                "UPDATE boards SET name = %s WHERE id = %s AND user_id = %s",
                (name, board_id, user_id),
            )
            updated = cursor.rowcount > 0
            connection.commit()
            return updated
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()

    @staticmethod
    def _decode_board_json(raw_value: Any) -> dict[str, Any]:
        if isinstance(raw_value, dict):
            return raw_value
        if isinstance(raw_value, (bytes, bytearray)):
            return json.loads(raw_value.decode("utf-8"))
        if isinstance(raw_value, str):
            return json.loads(raw_value)
        raise ValueError("Unexpected board_json value type.")
