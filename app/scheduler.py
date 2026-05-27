
# 自动化任务调度器
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.models.auto_task import AutoTaskRepository
from app.models.watch import WatchRepository
import requests
from bs4 import BeautifulSoup

# 全局调度器实例
_scheduler = None

def get_scheduler():
    """获取全局调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    return _scheduler

def _parse_baidu_news(soup, keyword, source_id):
    """解析百度新闻数据"""
    news_list = []
    try:
        items = soup.select("div.result-op")
        if not items:
            items = soup.select("div.c-container")
        for item in items[:10]:
            title_elem = item.select_one("h3 a, a")
            if not title_elem:
                continue
            title = title_elem.get_text(strip=True)
            url = title_elem.get("href", "")
            if not url:
                continue
            content_elem = item.select_one("div.c-abstract, p")
            content = content_elem.get_text(strip=True) if content_elem else ""
            time_elem = item.select_one("span.c-author, span.c-time")
            publish_time = time_elem.get_text(strip=True) if time_elem else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            news_list.append({
                "source_id": source_id,
                "keyword": keyword,
                "title": title,
                "content": content,
                "url": url,
                "publish_time": publish_time
            })
    except Exception:
        pass
    return news_list

def execute_auto_task(task_id):
    """执行自动化任务"""
    try:
        task = AutoTaskRepository.get_task_by_id(task_id)
        if not task:
            return
        
        source = WatchRepository.get_source_by_id(task["source_id"])
        if not source:
            AutoTaskRepository.add_log(
                task_id,
                task["name"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "error",
                0,
                "采集源不存在"
            )
            return
        
        url_pattern = source["url_pattern"]
        headers = source.get("headers", "{}")
        
        import json
        try:
            headers = json.loads(headers)
        except:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        url = url_pattern.replace("{关键词}", task["keyword"]).replace("{分页}", "1")
        session = requests.Session()
        
        response = session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        news_list = _parse_baidu_news(soup, task["keyword"], source["id"])
        
        total_found = len(news_list[:task["collect_count"]])
        total_saved = 0
        for news in news_list[:task["collect_count"]]:
            try:
                success = WatchRepository.add_watch_data(
                    news["source_id"],
                    news["keyword"],
                    news["title"],
                    news["content"],
                    news["url"],
                    news["publish_time"],
                    is_auto=1  # 标记为自动采集
                )
                if success:
                    total_saved += 1
            except Exception:
                pass
        
        # 记录日志
        if total_saved > 0:
            log_status = "success"
            log_msg = "成功采集 " + str(total_saved) + " 条新数据（共发现 " + str(total_found) + " 条）"
        else:
            log_status = "warning"
            log_msg = "未发现新数据（共发现 " + str(total_found) + " 条，均为重复）"
        AutoTaskRepository.add_log(
            task_id,
            task["name"],
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            log_status,
            total_saved,
            log_msg
        )
        
        # 更新任务最后运行时间
        AutoTaskRepository.update_task_last_run(task_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        return total_saved
    except Exception as e:
        AutoTaskRepository.add_log(
            task_id,
            "",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "error",
            0,
            str(e)
        )
        return 0

def init_scheduler():
    """初始化调度器并加载已启动的任务"""
    scheduler = get_scheduler()
    
    # 从数据库加载已启动的任务
    try:
        active_tasks = AutoTaskRepository.get_active_tasks()
    except:
        active_tasks = []
    
    for task in active_tasks:
        add_task_to_scheduler(task)
    
    if not scheduler.running:
        scheduler.start()
        logging.info("调度器已启动")

def add_task_to_scheduler(task):
    """添加任务到调度器"""
    scheduler = get_scheduler()
    
    # 检查任务是否已存在，先移除
    job_id = "auto_task_" + str(task["id"])
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    
    # 根据间隔单位计算间隔
    interval_value = task["interval_value"]
    interval_unit = task["interval_unit"]
    
    trigger_kwargs = {}
    if interval_unit == "seconds":
        trigger_kwargs["seconds"] = interval_value
    elif interval_unit == "minutes":
        trigger_kwargs["minutes"] = interval_value
    elif interval_unit == "hours":
        trigger_kwargs["hours"] = interval_value
    elif interval_unit == "days":
        trigger_kwargs["days"] = interval_value
    else:
        trigger_kwargs["seconds"] = 60
    
    # 添加任务
    scheduler.add_job(
        execute_auto_task,
        trigger=IntervalTrigger(**trigger_kwargs),
        id=job_id,
        args=[task["id"]],
        replace_existing=True
    )
    logging.info("任务已添加到调度器: " + task["name"])

def remove_task_from_scheduler(task_id):
    """从调度器中移除任务"""
    scheduler = get_scheduler()
    job_id = "auto_task_" + str(task_id)
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logging.info("任务已从调度器中移除: " + str(task_id))

def start_task(task_id):
    """启动任务"""
    task = AutoTaskRepository.get_task_by_id(task_id)
    if task:
        AutoTaskRepository.update_task_status(task_id, 1)
        add_task_to_scheduler(task)
        return True
    return False

def stop_task(task_id):
    """停止任务"""
    AutoTaskRepository.update_task_status(task_id, 0)
    remove_task_from_scheduler(task_id)
    return True

def shutdown_scheduler():
    """关闭调度器"""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        _scheduler = None
        logging.info("调度器已关闭")

