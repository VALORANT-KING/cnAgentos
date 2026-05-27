
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.db import get_connection
from app.models.auto_task import AutoTaskRepository
from app.models.watch import WatchRepository
from app.scheduler import execute_auto_task


def check_database():
    print("=== 检查数据库结构 ===")
    with get_connection() as conn:
        # 检查 auto_tasks 表
        print("\n1. auto_tasks 表结构:")
        cursor = conn.execute("PRAGMA table_info(auto_tasks)")
        for row in cursor.fetchall():
            print(f"  {row}")
        
        # 检查 watch_data 表
        print("\n2. watch_data 表结构:")
        cursor = conn.execute("PRAGMA table_info(watch_data)")
        for row in cursor.fetchall():
            print(f"  {row}")
            
        # 检查是否有 is_auto 字段
        print("\n3. 检查 is_auto 字段是否存在:")
        cursor = conn.execute("PRAGMA table_info(watch_data)")
        has_is_auto = any(col[1] == 'is_auto' for col in cursor.fetchall())
        print(f"  is_auto 字段存在: {has_is_auto}")
        
        # 查看现有任务
        print("\n4. 现有自动化任务:")
        tasks, total = AutoTaskRepository.get_all_tasks(1, 10)
        print(f"  共有 {total} 个任务")
        for task in tasks:
            print(f"    - ID: {task['id']}, 名称: {task['name']}, 状态: {task['status']}")
            
        # 查看采集源
        print("\n5. 现有采集源:")
        sources = WatchRepository.get_all_sources()
        for src in sources:
            print(f"    - ID: {src['id']}, 名称: {src['name']}")
            
        return has_is_auto


def add_is_auto_column():
    """添加 is_auto 字段到 watch_data 表"""
    print("\n=== 添加 is_auto 字段 ===")
    try:
        with get_connection() as conn:
            conn.execute("ALTER TABLE watch_data ADD COLUMN is_auto INTEGER NOT NULL DEFAULT 0")
            conn.commit()
            print("  ✓ is_auto 字段添加成功")
            return True
    except Exception as e:
        print(f"  ⚠️ 添加字段可能已存在: {str(e)}")
        # 检查字段是否真的存在
        cursor = conn.execute("PRAGMA table_info(watch_data)")
        for row in cursor.fetchall():
            print(f"    {row}")
        return True


def test_manual_execution(task_id):
    """手动执行任务测试"""
    print(f"\n=== 手动执行任务 ID: {task_id} ===")
    try:
        result = execute_auto_task(task_id)
        print(f"  ✓ 任务执行完成，采集到 {result} 条数据")
        return result
    except Exception as e:
        print(f"  ✗ 任务执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0


if __name__ == "__main__":
    print("自动化任务测试工具")
    print("="*50)
    
    # 检查数据库
    has_is_auto = check_database()
    
    # 如果没有 is_auto 字段，添加它
    if not has_is_auto:
        add_is_auto_column()
    
    # 查找第一个任务
    tasks, total = AutoTaskRepository.get_all_tasks(1, 1)
    if total > 0:
        task_id = tasks[0]['id']
        # 测试执行
        test_manual_execution(task_id)
        
        # 检查数据是否保存
        print("\n=== 检查是否保存自动采集数据 ===")
        data_list, data_total = WatchRepository.get_auto_data(1, 10)
        print(f"  自动采集的数据共有 {data_total} 条")
        for data in data_list:
            print(f"    - ID: {data['id']}, 标题: {data['title']}, is_auto: {data.get('is_auto')}")
    else:
        print("\n⚠️ 没有找到任务，请先在管理后台创建一个任务")
