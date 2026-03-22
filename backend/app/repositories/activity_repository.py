from __future__ import annotations

import json
from typing import Any

from app.db import db_connection, ensure_user_id


class ActivityRepository:
    def log_activity(
        self, board_id: int, username: str, action: str, details: dict[str, Any] | None = None
    ) -> None:
        with db_connection() as (connection, cursor):
            user_id = ensure_user_id(cursor, username)
            cursor.execute(
                "INSERT INTO board_activity (board_id, user_id, action, details) "
                "VALUES (%s, %s, %s, %s)",
                (board_id, user_id, action, json.dumps(details) if details else None),
            )

    def list_activity(
        self, board_id: int, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        with db_connection(commit=False) as (connection, cursor):
            cursor.execute(
                "SELECT ba.id, ba.action, ba.details, ba.created_at, u.username "
                "FROM board_activity ba JOIN users u ON ba.user_id = u.id "
                "WHERE ba.board_id = %s ORDER BY ba.created_at DESC "
                "LIMIT %s OFFSET %s",
                (board_id, limit, offset),
            )
            rows = cursor.fetchall()
            results = []
            for row in rows:
                details_raw = row[2]
                if isinstance(details_raw, str):
                    details = json.loads(details_raw)
                elif isinstance(details_raw, (bytes, bytearray)):
                    details = json.loads(details_raw.decode("utf-8"))
                elif isinstance(details_raw, dict):
                    details = details_raw
                else:
                    details = None
                results.append({
                    "id": int(row[0]),
                    "action": str(row[1]),
                    "details": details,
                    "created_at": str(row[3]),
                    "username": str(row[4]),
                })
            return results
