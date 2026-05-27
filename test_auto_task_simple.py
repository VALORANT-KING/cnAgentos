
import sqlite3
import sys
import os
import io

# 设置编码避免错误
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.db import get_connection
from app.models.auto_task import AutoTaskRepository
from app.models.watch import WatchRepository
from app.scheduler import execute_auto_task


def test_manual_execution(task_id):
    """手动执行任务测试"""
    print(f"\n--- 手动执行任务 ID: {task_id} ---")
    try:
        result = execute_auto_task(task_id)
        print(f"OK 任务执行完成，采集到 {result} 条数据")
        return result
    except Exception as e:
        print(f"ERROR 任务执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0


if __name__ == "__main__":
    print("自动化任务测试工具")
    print("="*50)
    
    # 查找第一个任务
    tasks, total = AutoTaskRepository.get_all_tasks(1, 1)
    if total > 0:
        task_id = tasks[0]['id']
        # 测试执行
        saved_count = test_manual_execution(task_id)
        
        # 检查数据是否保存
        print("\n--- 检查自动采集数据 ---")
        data_list, data_total = WatchRepository.get_auto_data(1, 10)
        print(f"自动采集的数据共有 {data_total} 条")
        for data in data_list[:3]:
            print(f"  - ID: {data['id']}, 标题: {data['title'][:30] if data.get('title') else 'None'}")
    else:
        print("\n没有找到任务，请先在管理后台创建一个任务")
