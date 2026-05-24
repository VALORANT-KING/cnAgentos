import json
import sqlite3
from app.models.db import get_connection


class DigitalEmployeeRepository:
    @staticmethod
    def get_list(page=1, page_size=20, keyword=None):
        offset = (page - 1) * page_size
        query = "SELECT e.*, COALESCE(a.name, '') as api_service_name FROM digital_employees e LEFT JOIN api_services a ON e.api_service_id = a.id"
        count_query = "SELECT COUNT(*) FROM digital_employees e"
        params = []
        count_params = []

        if keyword:
            where_clause = " WHERE e.name LIKE ? OR e.alias LIKE ? OR e.description LIKE ?"
            query += where_clause
            count_query += where_clause
            kw = f"%{keyword}%"
            params.extend([kw, kw, kw])
            count_params.extend([kw, kw, kw])

        query += " ORDER BY e.sort_order ASC, e.id DESC LIMIT ? OFFSET ?"
        params.extend([page_size, offset])

        with get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            total = conn.execute(count_query, count_params).fetchone()[0]
            return [dict(row) for row in rows], total

    @staticmethod
    def get_all():
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM digital_employees WHERE status = 1 ORDER BY sort_order ASC").fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(emp_id):
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM digital_employees WHERE id = ?", (emp_id,)).fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_by_alias(alias):
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM digital_employees WHERE alias = ?", (alias,)).fetchone()
            return dict(row) if row else None

    @staticmethod
    def add(name, alias, category="AI", agent_type="chat", api_service_id=0, prompt="", icon="fa-robot", description="", sort_order=0):
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO digital_employees (name, alias, category, agent_type, api_service_id, prompt, icon, description, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (name, alias, category, agent_type, api_service_id, prompt, icon, description, sort_order)
            )
            conn.commit()
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    @staticmethod
    def update(emp_id, name, alias, category="AI", agent_type="chat", api_service_id=0, prompt="", icon="fa-robot", description="", sort_order=0, status=1):
        with get_connection() as conn:
            conn.execute(
                "UPDATE digital_employees SET name=?, alias=?, category=?, agent_type=?, api_service_id=?, prompt=?, icon=?, description=?, sort_order=?, status=? WHERE id=?",
                (name, alias, category, agent_type, api_service_id, prompt, icon, description, sort_order, status, emp_id)
            )
            conn.commit()

    @staticmethod
    def delete(emp_id):
        with get_connection() as conn:
            conn.execute("DELETE FROM digital_employees WHERE id = ?", (emp_id,))
            conn.commit()
