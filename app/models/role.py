from app.models.db import as_int, get_connection

class RoleRepository:
    @staticmethod
    def get_all_roles() -> list:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, name, description, is_system, status, create_at FROM roles ORDER BY is_system DESC, id ASC"
            ).fetchall()
            return [{
                "id": r["id"], "name": r["name"], "description": r["description"],
                "is_system": r["is_system"], "status": r["status"], "create_at": r["create_at"]
            } for r in rows]

    @staticmethod
    def add_role(name: str, description: str) -> bool:
        try:
            with get_connection() as conn:
                conn.execute(
                    "INSERT INTO roles(name, description) VALUES(?,?)", (name, description)
                )
                conn.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def update_role(role_id: int, name: str, description: str, status: int) -> bool:
        try:
            with get_connection() as conn:
                conn.execute(
                    "UPDATE roles SET name=?, description=?, status=? WHERE id=? AND is_system=0",
                    (name, description, status, role_id)
                )
                conn.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def delete_role(role_id: int) -> bool:
        try:
            with get_connection() as conn:
                conn.execute("DELETE FROM roles WHERE id=? AND is_system=0", (role_id,))
                conn.execute("DELETE FROM role_permissions WHERE role_id=?", (role_id,))
                conn.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def get_role_permissions(role_id: int) -> list:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT module_id FROM role_permissions WHERE role_id = ?", (role_id,)
            ).fetchall()
            return [as_int(r["module_id"]) for r in rows]

    @staticmethod
    def save_role_permissions(role_id: int, module_ids: list) -> bool:
        try:
            with get_connection() as conn:
                conn.execute("DELETE FROM role_permissions WHERE role_id = ?", (role_id,))
                for mid in module_ids:
                    conn.execute(
                        "INSERT INTO role_permissions(role_id, module_id) VALUES(?,?)",
                        (role_id, mid)
                    )
                conn.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def get_roles_for_select() -> list:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, name FROM roles WHERE status = 1 ORDER BY is_system DESC, id ASC"
            ).fetchall()
            return [{"id": r["id"], "name": r["name"]} for r in rows]
