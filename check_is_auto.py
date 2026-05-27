
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.db import get_connection


def check_is_auto_field():
    print("检查 watch_data 表中的 is_auto 字段")
    print("="*50)
    
    with get_connection() as conn:
        # 检查现有的数据
        cursor = conn.execute("SELECT id, title, is_auto, create_at FROM watch_data ORDER BY id DESC LIMIT 10")
        print("\n最近 10 条数据:")
        for row in cursor.fetchall():
            print(f"  ID: {row[0]}, is_auto: {row[2]}, 标题: {row[1][:20] if row[1] else 'None'}")
        
        # 统计
        print("\n统计:")
        total = conn.execute("SELECT COUNT(*) FROM watch_data").fetchone()[0]
        auto_count = conn.execute("SELECT COUNT(*) FROM watch_data WHERE is_auto = 1").fetchone()[0]
        manual_count = conn.execute("SELECT COUNT(*) FROM watch_data WHERE is_auto = 0 OR is_auto IS NULL").fetchone()[0]
        print(f"  总数据数: {total}")
        print(f"  自动采集 (is_auto=1): {auto_count}")
        print(f"  手动采集/未标记: {manual_count}")
        
        # 如果有未标记的数据，把它们更新
        if manual_count > 0:
            print(f"\n更新未标记的数据...")
            conn.execute("UPDATE watch_data SET is_auto = 0 WHERE is_auto IS NULL OR is_auto != 1")
            conn.commit()
            print("  完成!")


if __name__ == "__main__":
    check_is_auto_field()
