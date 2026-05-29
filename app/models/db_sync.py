"""将 SQLite（init_db 后的完整库）同步到 MySQL，使 MySQL 初始化与 SQLite 一致。"""
import os
import sqlite3

from app.models.db import DB_PATH, init_db


def _mysql_type(col):
    name = (col[1] or "").upper()
    pk = col[5]
    if pk:
        return "INT AUTO_INCREMENT PRIMARY KEY"
    if name in ("INTEGER", "INT"):
        return "INT"
    if name == "REAL":
        return "DOUBLE"
    if name == "BLOB":
        return "LONGBLOB"
    return "TEXT"


def _cfg_to_mysql_connect(cfg):
    import pymysql

    return pymysql.connect(
        host=cfg.get("host") or "127.0.0.1",
        port=int(cfg.get("port") or 3306),
        user=cfg.get("username") or cfg.get("user") or "root",
        password=cfg.get("password") or "",
        database=cfg.get("database_name") or cfg.get("database") or "",
        charset="utf8mb4",
        autocommit=False,
    )


def mysql_is_initialized(cfg):
    """检查 MySQL 是否已有核心业务表（以 users 表为准）。"""
    try:
        conn = _cfg_to_mysql_connect(cfg)
        cur = conn.cursor()
        cur.execute("SHOW TABLES LIKE 'users'")
        row = cur.fetchone()
        cur.close()
        conn.close()
        return bool(row)
    except Exception:
        return False


def sync_sqlite_to_mysql(mysql_cfg, sqlite_path=None):
    """
    把 SQLite 中除 db_configs 外的所有表结构及数据复制到 MySQL。
    与 init_db() 完成后的 SQLite 保持一致。
    """
    import pymysql

    sqlite_path = sqlite_path or DB_PATH
    if not os.path.isfile(sqlite_path):
        raise FileNotFoundError("SQLite 文件不存在: " + sqlite_path)

    src = sqlite3.connect(sqlite_path)
    src.row_factory = sqlite3.Row

    dst = _cfg_to_mysql_connect(mysql_cfg)

    tables = [
        r[0]
        for r in src.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' AND name != 'db_configs' ORDER BY name"
        ).fetchall()
    ]

    cur = dst.cursor()
    cur.execute("SET FOREIGN_KEY_CHECKS=0")

    synced = 0
    total_rows = 0
    for table in tables:
        cols = src.execute("PRAGMA table_info(%s)" % table).fetchall()
        if not cols:
            continue

        col_defs = []
        col_names = []
        for c in cols:
            col_names.append(c[1])
            col_defs.append("`%s` %s" % (c[1], _mysql_type(c)))

        cur.execute("DROP TABLE IF EXISTS `%s`" % table)
        cur.execute(
            "CREATE TABLE `%s` (%s) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
            % (table, ", ".join(col_defs))
        )

        rows = src.execute("SELECT * FROM `%s`" % table).fetchall()
        if rows:
            placeholders = ", ".join(["%s"] * len(col_names))
            col_sql = ", ".join(["`%s`" % c for c in col_names])
            sql = "INSERT INTO `%s` (%s) VALUES (%s)" % (table, col_sql, placeholders)
            data = [tuple(row[c] for c in col_names) for row in rows]
            cur.executemany(sql, data)
            total_rows += len(rows)

        synced += 1

    cur.execute("SET FOREIGN_KEY_CHECKS=1")
    dst.commit()
    cur.close()
    dst.close()
    src.close()
    return synced, total_rows


def ensure_mysql_initialized(mysql_cfg, sqlite_path=None, force=False):
    """
    确保 MySQL 与 SQLite 初始化一致：
    1. 先执行 init_db() 保证 SQLite 完整
    2. 若 MySQL 未初始化或 force=True，则从 SQLite 全量同步
    """
    init_db()
    if not force and mysql_is_initialized(mysql_cfg):
        return True, "MySQL 已初始化，与 SQLite 结构一致"

    try:
        n_tables, n_rows = sync_sqlite_to_mysql(mysql_cfg, sqlite_path)
        return True, "已从 SQLite 同步 %d 张表、%d 行数据到 MySQL" % (n_tables, n_rows)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, "MySQL 同步失败: " + str(e)
