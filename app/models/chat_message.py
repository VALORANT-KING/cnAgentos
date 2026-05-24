import sqlite3
from app.models.db import get_connection


class ChatMessageRepository:
    @staticmethod
    def get_by_session(session_id):
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY id ASC",
                (session_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def add(session_id, role, content, msg_type="text", employee_id=0):
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO chat_messages (session_id, role, content, msg_type, employee_id) VALUES (?, ?, ?, ?, ?)",
                (session_id, role, content, msg_type, employee_id)
            )
            conn.commit()
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]
