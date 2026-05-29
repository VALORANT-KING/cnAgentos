#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键配置 MySQL + 从 SQLite 同步初始化（与 init_db 结果一致）

用法:
  python setup_mysql.py --password 你的MySQL密码
  python setup_mysql.py --password 你的密码 --switch
  python setup_mysql.py --password 你的密码 --force   # 强制重新从 SQLite 同步
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

DEFAULT_SQLITE = os.path.join(ROOT, "env", "database", "app.db")


def ensure_mysql_config(mysql_cfg, set_active=False):
    from app.models.db import init_db, reload_db_config
    from app.models.db_config import DbConfigRepository

    db_name = mysql_cfg.get("database_name") or mysql_cfg.get("database") or ""
    username = mysql_cfg.get("username") or mysql_cfg.get("user") or "root"
    host = mysql_cfg.get("host") or "127.0.0.1"
    port = mysql_cfg.get("port") or 3306
    password = mysql_cfg.get("password") or ""

    init_db()
    reload_db_config()

    existing = None
    for item in DbConfigRepository.get_list():
        if item.get("db_type") == "mysql" and item.get("database_name") == db_name:
            existing = item
            break

    if existing:
        config_id = existing["id"]
        DbConfigRepository.update(
            config_id, "本地 MySQL 8.0", "mysql", host, port, db_name, username, password,
        )
        print("[配置] 已更新已有 MySQL 配置 (id=%s)" % config_id)
    else:
        DbConfigRepository.add(
            "本地 MySQL 8.0", "mysql", host, port, db_name, username, password,
        )
        rows = DbConfigRepository.get_list()
        config_id = [r for r in rows if r["db_type"] == "mysql"][-1]["id"]
        print("[配置] 已新增 MySQL 配置 (id=%s)" % config_id)

    if set_active:
        ok, msg = DbConfigRepository.switch(config_id)
        print("[切换] %s" % msg)
    else:
        print("[配置] SQLite 仍为当前使用；到后台可手动切换 MySQL")


def main():
    parser = argparse.ArgumentParser(description="MySQL 初始化（与 SQLite 一致）并注册双库切换")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", default="")
    parser.add_argument("--database", default="cn_agentos")
    parser.add_argument("--sqlite", default=DEFAULT_SQLITE)
    parser.add_argument("--switch", action="store_true", help="完成后切换到 MySQL")
    parser.add_argument("--force", action="store_true", help="强制从 SQLite 重新同步到 MySQL")
    args = parser.parse_args()

    if not args.password:
        if not sys.stdin.isatty():
            print("非交互环境请使用: python setup_mysql.py --password 你的MySQL密码")
            sys.exit(1)
        try:
            import getpass
            args.password = getpass.getpass("请输入 MySQL 密码 (用户 %s): " % args.user)
        except Exception:
            pass

    print("=" * 50)
    print("MySQL 初始化（与 SQLite 一致）")
    print("=" * 50)

    try:
        import pymysql
    except ImportError:
        print("请先安装: pip install pymysql")
        sys.exit(1)

    from app.models.db import init_db, test_connection_with_config
    from app.models.db_sync import ensure_mysql_initialized

    mysql_cfg = {
        "db_type": "mysql",
        "host": args.host,
        "port": args.port,
        "username": args.user,
        "password": args.password,
        "database_name": args.database,
    }

    print("\n[1/3] 初始化 SQLite（init_db）...")
    init_db()
    print("  [OK] %s" % args.sqlite)

    print("\n[2/3] 创建 MySQL 数据库并测试连接...")
    conn = pymysql.connect(
        host=args.host, port=args.port, user=args.user,
        password=args.password, charset="utf8mb4",
    )
    conn.cursor().execute(
        "CREATE DATABASE IF NOT EXISTS `%s` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        % args.database
    )
    conn.commit()
    conn.close()
    ok, msg = test_connection_with_config(mysql_cfg)
    if not ok:
        print("连接失败:", msg)
        sys.exit(1)
    print("  [OK] %s" % msg)

    print("\n[3/3] 从 SQLite 同步表结构与数据到 MySQL...")
    ok, msg = ensure_mysql_initialized(mysql_cfg, args.sqlite, force=args.force)
    if not ok:
        print("  [失败]", msg)
        sys.exit(1)
    print("  [OK]", msg)

    print("\n[4/4] 注册后台数据库配置...")
    ensure_mysql_config(mysql_cfg, set_active=args.switch)

    print("\n" + "=" * 50)
    print("完成！后台: http://127.0.0.1:10086/admin/db/config")
    print("=" * 50)


if __name__ == "__main__":
    main()
