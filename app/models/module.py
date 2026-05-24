from app.models.db import get_connection

class ModuleRepository:
    @staticmethod
    def get_all_modules() -> list:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, name, icon, url, parent_id, sort_order, status, create_at FROM modules ORDER BY sort_order"
            ).fetchall()
            result = []
            for r in rows:
                result.append({
                    "id": r["id"], "name": r["name"], "icon": r["icon"],
                    "url": r["url"], "parent_id": r["parent_id"],
                    "sort_order": r["sort_order"], "status": r["status"],
                    "create_at": r["create_at"]
                })
            return result

    @staticmethod
    def get_module_tree() -> list:
        modules = ModuleRepository.get_all_modules()
        parents = [m for m in modules if m["parent_id"] == 0 and m["status"] == 1]
        result = []
        for p in parents:
            children = [c for c in modules if c["parent_id"] == p["id"] and c["status"] == 1]
            children.sort(key=lambda x: x["sort_order"])
            result.append({
                "id": p["id"], "name": p["name"], "icon": p["icon"],
                "children": children
            })
        return result

    @staticmethod
    def get_modules_by_role(role_id: int) -> list:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT module_id FROM role_permissions WHERE role_id = ?", (role_id,)
            ).fetchall()
            return [r["module_id"] for r in rows]

    @staticmethod
    def add_module(name: str, icon: str, url: str, parent_id: int, sort_order: int) -> bool:
        try:
            with get_connection() as conn:
                conn.execute(
                    "INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)",
                    (name, icon, url, parent_id, sort_order)
                )
                conn.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def update_module(module_id: int, name: str, icon: str, url: str, parent_id: int, sort_order: int, status: int) -> bool:
        try:
            with get_connection() as conn:
                conn.execute(
                    "UPDATE modules SET name=?, icon=?, url=?, parent_id=?, sort_order=?, status=? WHERE id=?",
                    (name, icon, url, parent_id, sort_order, status, module_id)
                )
                conn.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def delete_module(module_id: int) -> bool:
        try:
            with get_connection() as conn:
                conn.execute("DELETE FROM modules WHERE id = ?", (module_id,))
                conn.execute("DELETE FROM role_permissions WHERE module_id = ?", (module_id,))
                conn.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def get_parent_modules() -> list:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, name FROM modules WHERE parent_id = 0 AND status = 1 ORDER BY sort_order"
            ).fetchall()
            return [{"id": r["id"], "name": r["name"]} for r in rows]
