
# 自动化任务调度器
import logging
import random
import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.models.auto_task import AutoTaskRepository
from app.models.watch import WatchRepository
import requests
from bs4 import BeautifulSoup

# User-Agent 列表，用于轮换
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
]

# 全局调度器实例
_scheduler = None

def get_scheduler():
    """获取全局调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    return _scheduler

def _parse_baidu_news(soup, keyword, source_id):
    """解析新闻数据 - 支持多种采集源"""
    news_list = []
    try:
        # 百度新闻解析
        items = soup.select("div.result-op, div.c-container")
        if items:
            for item in items[:10]:
                title_elem = item.select_one("h3 a, a")
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                url = title_elem.get("href", "")
                if not url or not title:
                    continue
                content_elem = item.select_one("div.c-abstract, p")
                content = content_elem.get_text(strip=True) if content_elem else ""
                time_elem = item.select_one("span.c-author, span.c-time")
                publish_time = time_elem.get_text(strip=True) if time_elem else ""
                news_list.append({
                    "source_id": source_id,
                    "keyword": keyword,
                    "title": title,
                    "content": content,
                    "url": url if url.startswith("http") else "https://www.baidu.com" + url,
                    "publish_time": publish_time
                })
        
        # 如果没找到数据，尝试其他通用解析方式
        if not news_list:
            # 通用的文章列表解析
            items = soup.select("article, div[class*='item'], li[class*='item'], div[class*='news']")
            for item in items[:10]:
                title_elem = item.select_one("h1, h2, h3, h4, a[href]")
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                url = title_elem.get("href", "") if title_elem.name == "a" else ""
                if not url and title_elem.select_one("a"):
                    url = title_elem.select_one("a").get("href", "")
                if not title or not url:
                    continue
                content_elem = item.select_one("p, div[class*='abstract'], div[class*='content']")
                content = content_elem.get_text(strip=True) if content_elem else ""
                news_list.append({
                    "source_id": source_id,
                    "keyword": keyword,
                    "title": title,
                    "content": content,
                    "url": url if url.startswith("http") else "https://www.baidu.com" + url,
                    "publish_time": ""
                })
                
    except Exception as e:
        print(f"解析新闻数据出错: {e}")
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
            headers = {}
        
        # 构建完整的反爬虫 headers
        if not headers.get("User-Agent"):
            headers["User-Agent"] = random.choice(USER_AGENTS)
        
        # 添加常见的浏览器 headers
        default_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "Referer": "https://www.baidu.com/",
        }
        
        # 合并 headers（用户自定义的优先级更高）
        for key, value in default_headers.items():
            if key not in headers:
                headers[key] = value
        
        url = url_pattern.replace("{关键词}", task["keyword"]).replace("{分页}", "1")
        
        # 添加更长的随机延迟，避免请求过快
        time.sleep(random.uniform(3, 7))
        
        session = requests.Session()
        # 设置 session 的超时和重试
        session.mount('http://', requests.adapters.HTTPAdapter(max_retries=2))
        session.mount('https://', requests.adapters.HTTPAdapter(max_retries=2))
        
        # 先访问百度首页，模拟真实用户
        try:
            response = session.get("https://www.baidu.com", headers=headers, timeout=30, verify=False)
            time.sleep(random.uniform(1, 2))
        except:
            pass
        
        response = session.get(url, headers=headers, timeout=30, verify=False)
        
        # 检测是否跳转到验证码页面
        if "wappass.baidu.com" in response.url or "captcha" in response.text.lower():
            AutoTaskRepository.add_log(
                task_id,
                task["name"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "error",
                0,
                "触发百度验证码，请稍后再试或更换采集源"
            )
            # 更新任务最后运行时间
            AutoTaskRepository.update_task_last_run(task_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return 0
        
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
        error_msg = str(e)
        if "wappass.baidu.com" in error_msg or "验证码" in error_msg:
            error_msg = "触发百度验证码，请稍后再试或更换采集源"
        AutoTaskRepository.add_log(
            task_id,
            "",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "error",
            0,
            error_msg
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

