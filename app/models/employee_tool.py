import json
from app.models.db import get_connection


class EmployeeToolRepository:
    @staticmethod
    def get_list(page=1, page_size=20, keyword=None):
        offset = (page - 1) * page_size
        query = """
            SELECT t.*, COALESCE(a.name, '') AS api_service_name
            FROM employee_tools t
            LEFT JOIN api_services a ON t.api_service_id = a.id
        """
        count_query = "SELECT COUNT(*) FROM employee_tools t"
        params = []
        count_params = []
        if keyword:
            where = " WHERE t.name LIKE ? OR t.description LIKE ?"
            query += where
            count_query += where
            kw = f"%{keyword}%"
            params.extend([kw, kw])
            count_params.extend([kw, kw])
        query += " ORDER BY t.id DESC LIMIT ? OFFSET ?"
        params.extend([page_size, offset])
        with get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            total = conn.execute(count_query, count_params).fetchone()[0]
            return [dict(row) for row in rows], total

    @staticmethod
    def get_all_active():
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM employee_tools WHERE status = 1 ORDER BY id ASC"
            ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(tool_id):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM employee_tools WHERE id = ?", (tool_id,)
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def add(name, tool_type="api", api_service_id=0, config="", description=""):
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO employee_tools(name, tool_type, api_service_id, config, description)
                   VALUES(?,?,?,?,?)""",
                (name, tool_type, api_service_id, config, description),
            )
            conn.commit()
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    @staticmethod
    def update(tool_id, name, tool_type, api_service_id, config, description, status=1):
        with get_connection() as conn:
            conn.execute(
                """UPDATE employee_tools SET name=?, tool_type=?, api_service_id=?,
                   config=?, description=?, status=? WHERE id=?""",
                (name, tool_type, api_service_id, config, description, status, tool_id),
            )
            conn.commit()

    @staticmethod
    def delete(tool_id):
        with get_connection() as conn:
            conn.execute("DELETE FROM employee_tool_bindings WHERE tool_id = ?", (tool_id,))
            conn.execute("DELETE FROM employee_tools WHERE id = ?", (tool_id,))
            conn.commit()

    @staticmethod
    def get_bindings(employee_id):
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT t.* FROM employee_tools t
                JOIN employee_tool_bindings b ON b.tool_id = t.id
                WHERE b.employee_id = ? AND t.status = 1
                ORDER BY t.id ASC
                """,
                (employee_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_binding_ids(employee_id):
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT tool_id FROM employee_tool_bindings WHERE employee_id = ?",
                (employee_id,),
            ).fetchall()
            return [r["tool_id"] for r in rows]

    @staticmethod
    def save_bindings(employee_id, tool_ids):
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM employee_tool_bindings WHERE employee_id = ?",
                (employee_id,),
            )
            for tid in tool_ids:
                conn.execute(
                    "INSERT INTO employee_tool_bindings(employee_id, tool_id) VALUES(?,?)",
                    (employee_id, int(tid)),
                )
            conn.commit()
