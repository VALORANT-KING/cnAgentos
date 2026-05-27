import sqlite3
from app.models.db import get_connection

class AutoTaskRepository:
    @staticmethod
    def get_all_tasks(page=1, page_size=20):
        offset = (page - 1) * page_size
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT t.*, s.name as source_name FROM auto_tasks t LEFT JOIN watch_sources s ON t.source_id = s.id ORDER BY t.id DESC LIMIT ? OFFSET ?",
                (page_size, offset)
            ).fetchall()
            
            total = conn.execute("SELECT COUNT(*) FROM auto_tasks").fetchone()[0]
            
            return [dict(row) for row in rows], total

    @staticmethod
    def get_task_by_id(task_id):
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM auto_tasks WHERE id = ?", (task_id,)).fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_active_tasks():
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM auto_tasks WHERE status = 1").fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def add_task(name, task_type='collect', cron_expression=None, interval_value=60, interval_unit='seconds', source_id=0, keyword='', collect_count=10):
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO auto_tasks (name, task_type, cron_expression, interval_value, interval_unit, source_id, keyword, collect_count, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (name, task_type, cron_expression, interval_value, interval_unit, source_id, keyword, collect_count)
            )
            conn.commit()
            return cursor.lastrowid

    @staticmethod
    def update_task(task_id, name=None, task_type=None, cron_expression=None, interval_value=None, interval_unit=None, source_id=None, keyword=None, collect_count=None, status=None, last_run_time=None, next_run_time=None):
        with get_connection() as conn:
            updates = []
            params = []
            
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if task_type is not None:
                updates.append("task_type = ?")
                params.append(task_type)
            if cron_expression is not None:
                updates.append("cron_expression = ?")
                params.append(cron_expression)
            if interval_value is not None:
                updates.append("interval_value = ?")
                params.append(interval_value)
            if interval_unit is not None:
                updates.append("interval_unit = ?")
                params.append(interval_unit)
            if source_id is not None:
                updates.append("source_id = ?")
                params.append(source_id)
            if keyword is not None:
                updates.append("keyword = ?")
                params.append(keyword)
            if collect_count is not None:
                updates.append("collect_count = ?")
                params.append(collect_count)
            if status is not None:
                updates.append("status = ?")
                params.append(status)
            if last_run_time is not None:
                updates.append("last_run_time = ?")
                params.append(last_run_time)
            if next_run_time is not None:
                updates.append("next_run_time = ?")
                params.append(next_run_time)
            
            if not updates:
                return False
            
            params.append(task_id)
            query = f"UPDATE auto_tasks SET {', '.join(updates)} WHERE id = ?"
            conn.execute(query, params)
            conn.commit()
            return True

    @staticmethod
    def delete_task(task_id):
        with get_connection() as conn:
            conn.execute("DELETE FROM auto_tasks WHERE id = ?", (task_id,))
            conn.commit()

    @staticmethod
    def add_log(task_id, task_name, run_time, status='success', collected_count=0, error_message=''):
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO auto_task_logs (task_id, task_name, run_time, status, collected_count, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (task_id, task_name, run_time, status, collected_count, error_message)
            )
            conn.commit()

    @staticmethod
    def get_task_logs(task_id=None, page=1, page_size=20):
        offset = (page - 1) * page_size
        with get_connection() as conn:
            if task_id:
                rows = conn.execute(
                    "SELECT * FROM auto_task_logs WHERE task_id = ? ORDER BY id DESC LIMIT ? OFFSET ?",
                    (task_id, page_size, offset)
                ).fetchall()
                total = conn.execute("SELECT COUNT(*) FROM auto_task_logs WHERE task_id = ?", (task_id,)).fetchone()[0]
            else:
                rows = conn.execute(
                    "SELECT * FROM auto_task_logs ORDER BY id DESC LIMIT ? OFFSET ?",
                    (page_size, offset)
                ).fetchall()
                total = conn.execute("SELECT COUNT(*) FROM auto_task_logs").fetchone()[0]
            
            return [dict(row) for row in rows], total

    @staticmethod
    def update_task_status(task_id, status):
        """更新任务状态"""
        with get_connection() as conn:
            conn.execute(
                "UPDATE auto_tasks SET status = ? WHERE id = ?",
                (status, task_id)
            )
            conn.commit()
            return True

    @staticmethod
    def update_task_last_run(task_id, last_run_time):
        """更新任务最后执行时间"""
        with get_connection() as conn:
            conn.execute(
                "UPDATE auto_tasks SET last_run_time = ? WHERE id = ?",
                (last_run_time, task_id)
            )
            conn.commit()
            return True
