from app.models.db import get_connection

class ModelEngineRepository:
    @staticmethod
    def get_all_engines(page: int = 1, page_size: int = 6) -> tuple:
        offset = (page - 1) * page_size
        with get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) as cnt FROM model_engines").fetchone()["cnt"]
            rows = conn.execute(
                "SELECT * FROM model_engines ORDER BY is_default DESC, id DESC LIMIT ? OFFSET ?",
                (page_size, offset)
            ).fetchall()
            engines = []
            for r in rows:
                engines.append({
                    "id": r["id"], "name": r["name"], "provider": r["provider"],
                    "base_url": r["base_url"], "api_key": r["api_key"],
                    "model_name": r["model_name"], "type": r["type"],
                    "is_default": r["is_default"], "max_tokens": r["max_tokens"],
                    "temperature": r["temperature"], "status": r["status"],
                    "total_tokens": r["total_tokens"], "request_count": r["request_count"],
                    "description": r["description"], "create_at": r["create_at"]
                })
            return engines, total

    @staticmethod
    def get_engine_by_id(engine_id: int) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM model_engines WHERE id = ?", (engine_id,)
            ).fetchone()
            if not row:
                return None
            return {
                "id": row["id"], "name": row["name"], "provider": row["provider"],
                "base_url": row["base_url"], "api_key": row["api_key"],
                "model_name": row["model_name"], "type": row["type"],
                "is_default": row["is_default"], "max_tokens": row["max_tokens"],
                "temperature": row["temperature"], "status": row["status"],
                "total_tokens": row["total_tokens"], "request_count": row["request_count"],
                "description": row["description"], "create_at": row["create_at"]
            }

    @staticmethod
    def get_default_engine() -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM model_engines WHERE is_default = 1 AND status = 1 LIMIT 1"
            ).fetchone()
            if not row:
                row = conn.execute(
                    "SELECT * FROM model_engines WHERE status = 1 ORDER BY id LIMIT 1"
                ).fetchone()
            if not row:
                return None
            return {
                "id": row["id"], "name": row["name"], "provider": row["provider"],
                "base_url": row["base_url"], "api_key": row["api_key"],
                "model_name": row["model_name"], "type": row["type"],
                "is_default": row["is_default"], "max_tokens": row["max_tokens"],
                "temperature": row["temperature"], "status": row["status"],
                "total_tokens": row["total_tokens"], "request_count": row["request_count"],
                "description": row["description"], "create_at": row["create_at"]
            }

    @staticmethod
    def add_engine(name: str, provider: str, base_url: str, api_key: str,
                   model_name: str, engine_type: str, max_tokens: int,
                   temperature: float, description: str) -> bool:
        try:
            with get_connection() as conn:
                conn.execute(
                    """INSERT INTO model_engines(name, provider, base_url, api_key,
                    model_name, type, max_tokens, temperature, description)
                    VALUES(?,?,?,?,?,?,?,?,?)""",
                    (name, provider, base_url, api_key, model_name,
                     engine_type, max_tokens, temperature, description)
                )
                conn.commit()
            return True
        except Exception as e:
            print(f"添加模型引擎失败: {e}")
            return False

    @staticmethod
    def update_engine(engine_id: int, name: str, provider: str, base_url: str,
                      api_key: str, model_name: str, engine_type: str,
                      max_tokens: int, temperature: float, description: str,
                      status: int) -> bool:
        try:
            with get_connection() as conn:
                conn.execute(
                    """UPDATE model_engines SET name=?, provider=?, base_url=?,
                    api_key=?, model_name=?, type=?, max_tokens=?, temperature=?,
                    description=?, status=? WHERE id=?""",
                    (name, provider, base_url, api_key, model_name, engine_type,
                     max_tokens, temperature, description, status, engine_id)
                )
                conn.commit()
            return True
        except Exception as e:
            print(f"更新模型引擎失败: {e}")
            return False

    @staticmethod
    def delete_engine(engine_id: int) -> bool:
        try:
            with get_connection() as conn:
                row = conn.execute(
                    "SELECT is_default FROM model_engines WHERE id = ?", (engine_id,)
                ).fetchone()
                if row and row["is_default"] == 1:
                    return False
                conn.execute("DELETE FROM model_engines WHERE id = ?", (engine_id,))
                conn.commit()
            return True
        except Exception as e:
            print(f"删除模型引擎失败: {e}")
            return False

    @staticmethod
    def set_default_engine(engine_id: int) -> bool:
        try:
            with get_connection() as conn:
                conn.execute("UPDATE model_engines SET is_default = 0")
                conn.execute(
                    "UPDATE model_engines SET is_default = 1, status = 1 WHERE id = ?",
                    (engine_id,)
                )
                conn.commit()
            return True
        except Exception as e:
            print(f"设置默认引擎失败: {e}")
            return False

    @staticmethod
    def add_token_usage(engine_id: int, tokens: int) -> bool:
        try:
            with get_connection() as conn:
                conn.execute(
                    "UPDATE model_engines SET total_tokens = total_tokens + ?, request_count = request_count + 1 WHERE id = ?",
                    (tokens, engine_id)
                )
                conn.commit()
            return True
        except Exception:
            return False
