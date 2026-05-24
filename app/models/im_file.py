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
                "SELECT id, file_path, file_name FROM im_files WHERE file_hash = ?",
                (file_hash,),
            ).fetchone()
            if existing:
                return dict(existing)

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


class ImServerRepository:
    @staticmethod
    def get_active_servers():
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM im_servers WHERE status = 1 ORDER BY current_load ASC, id ASC"
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_all():
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM im_servers ORDER BY id DESC"
            ).fetchall()
            return [dict(r) for r in rows]
