import sqlite3
from app.models.db import get_connection


class ChatSessionRepository:
    @staticmethod
    def get_by_user(user_id, page=1, page_size=50):
        offset = (page - 1) * page_size
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM chat_sessions WHERE user_id = ? ORDER BY id DESC LIMIT ? OFFSET ?",
                (user_id, page_size, offset)
            ).fetchall()
            total = conn.execute("SELECT COUNT(*) FROM chat_sessions WHERE user_id = ?", (user_id,)).fetchone()[0]
            return [dict(r) for r in rows], total

    @staticmethod
    def get_by_id(session_id):
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
            return dict(row) if row else None

    @staticmethod
    def create(user_id, title="新对话", model_id=0):
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO chat_sessions (user_id, title, model_id) VALUES (?, ?, ?)",
                (user_id, title, model_id)
            )
            conn.commit()
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    @staticmethod
    def update_title(session_id, title):
        with get_connection() as conn:
            conn.execute("UPDATE chat_sessions SET title = ? WHERE id = ?", (title, session_id))
            conn.commit()

    @staticmethod
    def delete(session_id):
        with get_connection() as conn:
            conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            conn.commit()
