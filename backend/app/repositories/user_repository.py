from __future__ import annotations

from typing import Any

import bcrypt

from app.config import settings
from app.db import get_connection


class UserRepository:
    def create_user(self, username: str, password: str) -> int:
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        connection = None
        cursor = None
        try:
            connection = get_connection(database=settings.db_name)
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, password_hash),
            )
            user_id = int(cursor.lastrowid)
            connection.commit()
            return user_id
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        connection = None
        cursor = None
        try:
            connection = get_connection(database=settings.db_name)
            cursor = connection.cursor()
            cursor.execute(
                "SELECT id, username, password_hash FROM users WHERE username = %s",
                (username,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            password_hash = row[2]
            return {
                "id": int(row[0]),
                "username": str(row[1]),
                "password_hash": password_hash if password_hash is not None else None,
            }
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()

    def verify_password(self, password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode(), password_hash.encode())

    def get_profile(self, username: str) -> dict[str, Any] | None:
        connection = None
        cursor = None
        try:
            connection = get_connection(database=settings.db_name)
            cursor = connection.cursor()
            cursor.execute(
                "SELECT u.id, u.username, u.created_at, COUNT(b.id) AS board_count "
                "FROM users u LEFT JOIN boards b ON u.id = b.user_id "
                "WHERE u.username = %s GROUP BY u.id",
                (username,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return {
                "id": int(row[0]),
                "username": str(row[1]),
                "created_at": str(row[2]),
                "board_count": int(row[3]),
            }
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()

    def update_password(self, username: str, new_password: str) -> bool:
        new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        connection = None
        cursor = None
        try:
            connection = get_connection(database=settings.db_name)
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE username = %s",
                (new_hash, username),
            )
            updated = cursor.rowcount > 0
            connection.commit()
            return updated
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()

    def delete_user(self, username: str) -> bool:
        connection = None
        cursor = None
        try:
            connection = get_connection(database=settings.db_name)
            cursor = connection.cursor()
            cursor.execute(
                "DELETE FROM users WHERE username = %s",
                (username,),
            )
            deleted = cursor.rowcount > 0
            connection.commit()
            return deleted
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()
