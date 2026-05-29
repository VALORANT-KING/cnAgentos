import os
from app.models.db import get_meta_connection, reload_db_config, test_connection_with_config, DB_PATH, _project_root


def _row_to_dict(row):
    if row is None:
        return None
    return dict(row)


class DbConfigRepository:
    @staticmethod
    def get_list():
        with get_meta_connection() as conn:
            rows = conn.execute(
                "SELECT id, name, db_type, host, port, database_name, username, password, is_active, create_at "
                "FROM db_configs ORDER BY is_active DESC, id ASC"
            ).fetchall()
            data = []
            for row in rows:
                item = _row_to_dict(row)
                if item.get("password"):
                    item["password"] = "******"
                data.append(item)
            return data

    @staticmethod
    def get_by_id(config_id):
        with get_meta_connection() as conn:
            row = conn.execute("SELECT * FROM db_configs WHERE id = ?", (config_id,)).fetchone()
            return _row_to_dict(row)

    @staticmethod
    def get_active():
        with get_meta_connection() as conn:
            row = conn.execute("SELECT * FROM db_configs WHERE is_active = 1 LIMIT 1").fetchone()
            return _row_to_dict(row)

    @staticmethod
    def add(name, db_type, host, port, database_name, username, password):
        db_type = (db_type or "sqlite").lower()
        if db_type == "sqlite":
            database_name = DbConfigRepository._normalize_sqlite_path(database_name)
        with get_meta_connection() as conn:
            conn.execute(
                """INSERT INTO db_configs(name, db_type, host, port, database_name, username, password, is_active)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (name, db_type, host or "", int(port or 3306), database_name or "", username or "", password or "", 0),
            )
            conn.commit()

    @staticmethod
    def update(config_id, name, db_type, host, port, database_name, username, password):
        existing = DbConfigRepository.get_by_id(config_id)
        if not existing:
            return False
        db_type = (db_type or "sqlite").lower()
        if db_type == "sqlite":
            database_name = DbConfigRepository._normalize_sqlite_path(database_name)
        final_password = password if password else existing.get("password", "")
        with get_meta_connection() as conn:
            conn.execute(
                """UPDATE db_configs
                   SET name=?, db_type=?, host=?, port=?, database_name=?, username=?, password=?
                   WHERE id=?""",
                (name, db_type, host or "", int(port or 3306), database_name or "", username or "", final_password, config_id),
            )
            conn.commit()
        return True

    @staticmethod
    def delete(config_id):
        active = DbConfigRepository.get_active()
        if active and active["id"] == config_id:
            return False, "不能删除当前正在使用的数据库配置"
        with get_meta_connection() as conn:
            conn.execute("DELETE FROM db_configs WHERE id = ?", (config_id,))
            conn.commit()
        return True, "删除成功"

    @staticmethod
    def switch(config_id):
        target = DbConfigRepository.get_by_id(config_id)
        if not target:
            return False, "配置不存在"
        ok, msg = test_connection_with_config(target)
        if not ok:
            return False, msg
        init_msg = ""
        if (target.get("db_type") or "").lower() == "mysql":
            from app.models.db_sync import ensure_mysql_initialized
            ok_init, init_msg = ensure_mysql_initialized(target)
            if not ok_init:
                return False, init_msg
        with get_meta_connection() as conn:
            conn.execute("UPDATE db_configs SET is_active = 0")
            conn.execute("UPDATE db_configs SET is_active = 1 WHERE id = ?", (config_id,))
            conn.commit()
        reload_db_config()
        result = "已切换到: " + target.get("name", "")
        if init_msg:
            result += "（" + init_msg + "）"
        return True, result

    @staticmethod
    def test_config(config_id=None, payload=None):
        if config_id:
            cfg = DbConfigRepository.get_by_id(config_id)
        else:
            cfg = payload or {}
        if not cfg:
            return False, "配置不存在"
        if config_id and cfg.get("password") == "******":
            full = DbConfigRepository.get_by_id(config_id)
            cfg["password"] = full.get("password", "")
        return test_connection_with_config(cfg)

    @staticmethod
    def ensure_default_config():
        with get_meta_connection() as conn:
            count = conn.execute("SELECT COUNT(*) AS cnt FROM db_configs").fetchone()["cnt"]
            if count:
                return
            default_path = os.path.relpath(DB_PATH, _project_root()).replace("\\", "/")
            conn.execute(
                """INSERT INTO db_configs(name, db_type, host, port, database_name, username, password, is_active)
                   VALUES(?,?,?,?,?,?,?,?)""",
                ("默认 SQLite", "sqlite", "", 0, default_path, "", "", 1),
            )
            conn.commit()

    @staticmethod
    def _normalize_sqlite_path(path):
        path = (path or "").strip()
        if not path:
            return os.path.relpath(DB_PATH, _project_root()).replace("\\", "/")
        if os.path.isabs(path):
            return path
        return path.replace("\\", "/")
