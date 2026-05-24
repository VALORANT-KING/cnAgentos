import json
import sqlite3
from app.models.db import get_connection


class ApiServiceRepository:
    @staticmethod
    def get_list(page=1, page_size=20, keyword=None):
        offset = (page - 1) * page_size
        query = "SELECT * FROM api_services"
        count_query = "SELECT COUNT(*) FROM api_services"
        params = []
        count_params = []

        if keyword:
            where_clause = " WHERE name LIKE ? OR url LIKE ? OR description LIKE ?"
            query += where_clause
            count_query += where_clause
            kw = f"%{keyword}%"
            params.extend([kw, kw, kw])
            count_params.extend([kw, kw, kw])

        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([page_size, offset])

        with get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            total = conn.execute(count_query, count_params).fetchone()[0]
            return [dict(row) for row in rows], total

    @staticmethod
    def get_all():
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM api_services WHERE status = 1 ORDER BY id DESC").fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(api_id):
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM api_services WHERE id = ?", (api_id,)).fetchone()
            return dict(row) if row else None

    @staticmethod
    def add(name, url, method="GET", resp_format="JSON", qps_limit=0, token="", description=""):
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO api_services (name, url, method, resp_format, qps_limit, token, description) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, url, method, resp_format, qps_limit, token, description)
            )
            conn.commit()
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    @staticmethod
    def update(api_id, name, url, method="GET", resp_format="JSON", qps_limit=0, token="", status=1, description=""):
        with get_connection() as conn:
            conn.execute(
                "UPDATE api_services SET name=?, url=?, method=?, resp_format=?, qps_limit=?, token=?, status=?, description=? WHERE id=?",
                (name, url, method, resp_format, qps_limit, token, status, description, api_id)
            )
            conn.commit()

    @staticmethod
    def delete(api_id):
        with get_connection() as conn:
            conn.execute("DELETE FROM api_services WHERE id = ?", (api_id,))
            conn.commit()
