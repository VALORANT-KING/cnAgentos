import hashlib
import os

from app.models.db import get_connection, _project_root


UPLOAD_DIR = os.path.join(_project_root(), "uploads", "im")


class ImFileRepository:
    @staticmethod
    def ensure_upload_dir():
        os.makedirs(UPLOAD_DIR, exist_ok=True)

    @staticmethod
    def save_file(file_name, file_body, uploader_id):
        ImFileRepository.ensure_upload_dir()
        file_hash = hashlib.md5(file_body).hexdigest()
        with get_connection() as conn:
            existing = conn.execute(
                """
                SELECT id FROM im_files WHERE file_hash = ?
                """,
                (file_hash,),
            ).fetchone()
            if existing:
                return ImFileRepository.get_by_id(existing["id"])

        ext = os.path.splitext(file_name)[1]
        stored_name = f"{file_hash}{ext}"
        stored_path = os.path.join(UPLOAD_DIR, stored_name)
        with open(stored_path, "wb") as f:
            f.write(file_body)

        with get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO im_files(file_name, file_path, file_size, file_hash, uploader_id)
                VALUES(?, ?, ?, ?, ?)
                """,
                (file_name, stored_name, len(file_body), file_hash, uploader_id),
            )
            fid = cur.lastrowid
            conn.commit()
        return ImFileRepository.get_by_id(fid)

    @staticmethod
    def get_by_id(file_id):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM im_files WHERE id = ?",
                (file_id,),
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_full_path(file_record):
        return os.path.join(UPLOAD_DIR, file_record["file_path"])

    @staticmethod
    def get_list(page=1, page_size=20, keyword=None):
        offset = (page - 1) * page_size
        query = """
            SELECT f.*, u.username AS uploader_name
            FROM im_files f
            LEFT JOIN users u ON u.id = f.uploader_id
        """
        count_query = "SELECT COUNT(*) FROM im_files f"
        params = []
        count_params = []
        if keyword:
            where = " WHERE f.file_name LIKE ? OR f.file_hash LIKE ?"
            query += where
            count_query += where
            kw = f"%{keyword}%"
            params.extend([kw, kw])
            count_params.extend([kw, kw])
        query += " ORDER BY f.id DESC LIMIT ? OFFSET ?"
        params.extend([page_size, offset])
        with get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            total = conn.execute(count_query, count_params).fetchone()[0]
            return [dict(r) for r in rows], total

    @staticmethod
    def delete(file_id):
        record = ImFileRepository.get_by_id(file_id)
        if not record:
            return False
        path = ImFileRepository.get_full_path(record)
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
        with get_connection() as conn:
            conn.execute("DELETE FROM im_files WHERE id = ?", (file_id,))
            conn.commit()
        return True

    @staticmethod
    def is_previewable(file_name):
        ext = os.path.splitext(file_name)[1].lower()
        return ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".pdf", ".txt")


class ImServerRepository:
    @staticmethod
    def get_active_servers():
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM im_servers WHERE status = 1
                   ORDER BY priority DESC, current_load ASC, id ASC"""
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_all():
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM im_servers ORDER BY priority DESC, id DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_list(page=1, page_size=20):
        offset = (page - 1) * page_size
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM im_servers ORDER BY priority DESC, id DESC LIMIT ? OFFSET ?",
                (page_size, offset),
            ).fetchall()
            total = conn.execute("SELECT COUNT(*) FROM im_servers").fetchone()[0]
            return [dict(r) for r in rows], total

    @staticmethod
    def get_by_id(server_id):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM im_servers WHERE id = ?", (server_id,)
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def add(name, host, port, status=1, priority=0, current_load=0):
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO im_servers(name, host, port, status, priority, current_load)
                   VALUES(?,?,?,?,?,?)""",
                (name, host, port, status, priority, current_load),
            )
            conn.commit()
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    @staticmethod
    def update(server_id, name, host, port, status, priority, current_load):
        with get_connection() as conn:
            conn.execute(
                """UPDATE im_servers SET name=?, host=?, port=?, status=?,
                   priority=?, current_load=? WHERE id=?""",
                (name, host, port, status, priority, current_load, server_id),
            )
            conn.commit()

    @staticmethod
    def delete(server_id):
        with get_connection() as conn:
            conn.execute("DELETE FROM im_servers WHERE id = ?", (server_id,))
            conn.commit()
