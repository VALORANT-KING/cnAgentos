import json
import sqlite3
from app.models.db import as_int, get_connection, row_to_dict


def _rows_to_dicts(rows):
    return [row_to_dict(row) for row in rows]


class WatchRepository:
    @staticmethod
    def get_all_sources():
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM watch_sources ORDER BY id DESC").fetchall()
            return _rows_to_dicts(rows)

    @staticmethod
    def get_active_sources():
        """获取启用状态的瞭望源（供采集页使用）。"""
        sources = WatchRepository.get_all_sources()
        active = []
        for s in sources:
            status = s.get("status", 1)
            if status is None or int(status) == 1:
                active.append(s)
        return active

    @staticmethod
    def get_source_by_id(source_id):
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM watch_sources WHERE id = ?", (source_id,)).fetchone()
            return row_to_dict(row) if row else None

    @staticmethod
    def add_source(name, url_pattern, headers=None, params=None):
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO watch_sources (name, url_pattern, headers, params) VALUES (?, ?, ?, ?)",
                (name, url_pattern, headers, params)
            )
            conn.commit()

    @staticmethod
    def update_source(source_id, name, url_pattern, headers=None, params=None, status=1):
        with get_connection() as conn:
            conn.execute(
                "UPDATE watch_sources SET name=?, url_pattern=?, headers=?, params=?, status=? WHERE id=?",
                (name, url_pattern, headers, params, status, source_id)
            )
            conn.commit()

    @staticmethod
    def delete_source(source_id):
        with get_connection() as conn:
            conn.execute("DELETE FROM watch_sources WHERE id = ?", (source_id,))
            conn.commit()

    @staticmethod
    def get_all_data(page=1, page_size=20, keyword=None):
        offset = (page - 1) * page_size
        query = "SELECT d.*, s.name as source_name FROM watch_data d LEFT JOIN watch_sources s ON d.source_id = s.id"
        params = []
        if keyword:
            query += " WHERE d.title LIKE ? OR d.keyword LIKE ?"
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        query += " ORDER BY d.id DESC LIMIT ? OFFSET ?"
        params.extend([page_size, offset])
        
        with get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            
            count_query = "SELECT COUNT(*) FROM watch_data d"
            count_params = []
            if keyword:
                count_query += " WHERE d.title LIKE ? OR d.keyword LIKE ?"
                count_params.extend([f"%{keyword}%", f"%{keyword}%"])
            
            total = conn.execute(count_query, count_params).fetchone()[0]
            
            return _rows_to_dicts(rows), total

    @staticmethod
    def save_collected_data(source_id, keyword, data_list):
        """保存采集结果，返回实际新入库条数。"""
        source_id = as_int(source_id)
        inserted = 0
        with get_connection() as conn:
            for item in data_list:
                url = (item.get("url") or "").strip()
                if not url:
                    continue
                exists = conn.execute(
                    "SELECT id FROM watch_data WHERE url = ?", (url,)
                ).fetchone()
                if not exists:
                    conn.execute(
                        "INSERT INTO watch_data (source_id, keyword, title, content, url, publish_time) VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            source_id,
                            keyword,
                            item.get("title", ""),
                            item.get("content", ""),
                            url,
                            item.get("publish_time", ""),
                        ),
                    )
                    inserted += 1
            conn.commit()
        return inserted

    @staticmethod
    def delete_data(data_ids):
        if not data_ids:
            return
        placeholders = ','.join(['?'] * len(data_ids))
        with get_connection() as conn:
            conn.execute(f"DELETE FROM watch_data WHERE id IN ({placeholders})", data_ids)
            conn.commit()

    @staticmethod
    def add_watch_data(source_id, keyword, title, content, url, publish_time, is_auto=0):
        """添加采集数据，支持标记是否自动采集"""
        source_id = as_int(source_id)
        url = (url or "").strip()
        if not url:
            return False
        with get_connection() as conn:
            exists = conn.execute("SELECT id FROM watch_data WHERE url = ?", (url,)).fetchone()
            if exists:
                return False
            conn.execute(
                """
                INSERT INTO watch_data (source_id, keyword, title, content, url, publish_time, is_auto)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (source_id, keyword, title, content, url, publish_time, is_auto)
            )
            conn.commit()
            return True

    @staticmethod
    def get_auto_data(page=1, page_size=20, keyword=None):
        """获取自动采集的数据"""
        offset = (page - 1) * page_size
        query = "SELECT d.*, s.name as source_name FROM watch_data d LEFT JOIN watch_sources s ON d.source_id = s.id WHERE d.is_auto = 1"
        params = []
        if keyword:
            query += " AND (d.title LIKE ? OR d.keyword LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        query += " ORDER BY d.id DESC LIMIT ? OFFSET ?"
        params.extend([page_size, offset])
        
        with get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            
            count_query = "SELECT COUNT(*) FROM watch_data d WHERE d.is_auto = 1"
            count_params = []
            if keyword:
                count_query += " AND (d.title LIKE ? OR d.keyword LIKE ?)"
                count_params.extend([f"%{keyword}%", f"%{keyword}%"])
            
            total = conn.execute(count_query, count_params).fetchone()[0]
            
            return _rows_to_dicts(rows), total
