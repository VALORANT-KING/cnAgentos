import json
import re
import time
import asyncio
from datetime import datetime, timedelta
from collections import Counter

import tornado.web
import tornado.ioloop
from app.controllers.base import BaseHandler
from app.models.db import get_connection
from app.models.model_engine import ModelEngineRepository


STOP_WORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
    "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "些",
    "什么", "怎么", "如何", "为什么", "可以", "这个", "那个", "还是",
    "已经", "因为", "所以", "但是", "如果", "虽然", "而且", "或者",
    "不过", "然后", "之后", "之前", "以后", "以上", "以下", "以及",
    "就是", "只是", "还是", "还有", "不是", "不能", "不会", "不用",
    "不要", "可能", "应该", "需要", "一定", "必须", "能够", "是否",
    "目前", "现在", "今天", "昨天", "明天", "今年", "去年", "明年",
    "一个", "一种", "一些", "一下", "一点", "一片", "一边",
    "来", "去", "做", "让", "被", "把", "给", "对", "为", "从",
    "与", "以", "及", "等", "等等", "每", "各", "某", "本", "该",
    "其", "其中", "其他", "其它", "另外", "再", "又", "还",
    "比", "较", "更", "最", "非常", "十分", "特别", "尤其",
    "刚", "刚刚", "才", "就", "便", "即", "将", "正", "正在",
    "一直", "总是", "经常", "通常", "一般", "往往", "偶尔",
    "同时", "同样", "此外", "另外", "而且", "并且", "然而",
    "因此", "因为", "所以", "由于", "基于", "随着",
    "通过", "根据", "按照", "关于", "对于", "经过",
    "进行", "实现", "完成", "开始", "继续", "停止", "结束",
    "使用", "利用", "采用", "应用", "提供", "支持",
    "包括", "包含", "涉及", "有关", "相关",
    "主要", "重要", "关键", "基本", "根本", "核心",
    "方面", "领域", "范围", "层次", "水平",
    "情况", "状态", "程度", "结果", "效果", "影响",
    "问题", "方式", "方法", "途径", "手段", "措施",
    "作用", "功能", "性能", "特点", "特征", "优势",
    "发展", "变化", "趋势", "方向", "目标", "目的",
    "表示", "认为", "觉得", "知道", "了解", "明白",
    "发现", "注意", "关注", "重视", "强调", "指出",
    "存在", "发生", "产生", "出现", "形成", "构成",
    "具有", "拥有", "具备", "带有", "含有",
    "作为", "成为", "称为", "当作", "看作",
    "不同", "相同", "相似", "类似", "一样", "一致",
    "全国", "中国", "各省", "地区", "各级", "各地",
    "nbsp", "amp", "quot", "lt", "gt", "&nbsp;", "\r", "\n", "\t",
    " ", "", "\u3000", "\ufeff", "\xa0",
}


CHINA_CITY_COORDS = {
    "北京": (116.40, 39.90), "天津": (117.20, 39.13), "上海": (121.47, 31.23),
    "重庆": (106.55, 29.57), "广州": (113.26, 23.13), "深圳": (114.07, 22.62),
    "成都": (104.07, 30.67), "杭州": (120.16, 30.24), "武汉": (114.30, 30.60),
    "西安": (108.94, 34.26), "南京": (118.79, 32.06), "郑州": (113.65, 34.76),
    "长沙": (112.98, 28.19), "苏州": (120.59, 31.30), "沈阳": (123.43, 41.80),
    "青岛": (120.38, 36.07), "大连": (121.61, 38.91), "厦门": (118.08, 24.48),
    "宁波": (121.54, 29.87), "无锡": (120.31, 31.49), "合肥": (117.23, 31.82),
    "福州": (119.31, 26.08), "济南": (117.00, 36.67), "贵阳": (106.71, 26.57),
    "昆明": (102.83, 24.88), "长春": (125.32, 43.90), "哈尔滨": (126.53, 45.80),
    "太原": (112.55, 37.87), "石家庄": (114.51, 38.04), "兰州": (103.73, 36.03),
    "乌鲁木齐": (87.62, 43.82), "南宁": (108.37, 22.82), "海口": (110.33, 20.03),
    "南昌": (115.86, 28.68), "呼和浩特": (111.75, 40.84), "拉萨": (91.17, 29.65),
    "银川": (106.23, 38.47), "西宁": (101.78, 36.62), "温州": (120.70, 28.00),
    "珠海": (113.58, 22.27), "佛山": (113.12, 23.02), "东莞": (113.75, 23.05),
    "三亚": (109.51, 18.25), "桂林": (110.28, 25.28), "洛阳": (112.44, 34.62),
    "宜昌": (111.29, 30.69), "岳阳": (113.13, 29.36), "遵义": (106.92, 27.73),
    "包头": (109.84, 40.66), "唐山": (118.18, 39.63), "徐州": (117.18, 34.27),
    "金华": (119.65, 29.08), "绍兴": (120.58, 30.05), "泉州": (118.59, 24.91),
    "烟台": (121.39, 37.54), "威海": (122.12, 37.51), "柳州": (109.41, 24.32),
    "绵阳": (104.68, 31.47), "宜宾": (104.62, 28.77), "湛江": (110.39, 21.19),
    "中山": (113.38, 22.52), "汕头": (116.68, 23.35), "秦皇岛": (119.60, 39.93),
    "连云港": (119.22, 34.60), "扬州": (119.42, 32.39), "镇江": (119.44, 32.18),
    "保定": (115.46, 38.87), "邯郸": (114.48, 36.61), "大庆": (125.03, 46.59),
    "吉林": (126.55, 43.84), "齐齐哈尔": (123.97, 47.35), "锦州": (121.13, 41.10),
    "潍坊": (119.16, 36.72), "济宁": (116.59, 35.41), "泰安": (117.13, 36.20),
    "临沂": (118.35, 35.05), "襄阳": (112.12, 32.01), "荆州": (112.24, 30.33),
    "黄冈": (114.88, 30.45), "株洲": (113.13, 27.83), "湘潭": (112.94, 27.83),
    "衡阳": (112.57, 26.89), "九江": (115.99, 29.71), "赣州": (114.93, 25.83),
    "汕头": (116.68, 23.35), "肇庆": (112.46, 23.05), "惠州": (114.42, 23.11),
    "揭阳": (116.37, 23.55), "儋州": (109.58, 19.52), "大理": (100.23, 25.61),
    "丽江": (100.23, 26.88), "舟山": (122.21, 30.02), "大庆": (125.03, 46.59),
}


CHINA_PROVINCE_COORDS = {
    "四川": (104.07, 30.67), "广东": (113.26, 23.13), "江苏": (118.79, 32.06),
    "浙江": (120.16, 30.24), "山东": (117.00, 36.67), "河南": (113.65, 34.76),
    "河北": (114.51, 38.04), "湖南": (112.98, 28.19), "湖北": (114.30, 30.60),
    "福建": (119.31, 26.08), "安徽": (117.23, 31.82), "辽宁": (123.43, 41.80),
    "江西": (115.86, 28.68), "陕西": (108.94, 34.26), "山西": (112.55, 37.87),
    "贵州": (106.71, 26.57), "云南": (102.83, 24.88), "甘肃": (103.73, 36.03),
    "青海": (101.78, 36.62), "吉林": (125.32, 43.90), "黑龙江": (126.53, 45.80),
    "海南": (110.33, 20.03), "台湾": (121.50, 25.05), "新疆": (87.62, 43.82),
    "西藏": (91.17, 29.65), "内蒙古": (111.75, 40.84), "广西": (108.37, 22.82),
    "宁夏": (106.23, 38.47), "香港": (114.17, 22.28), "澳门": (113.55, 22.19),
}


PLACE_COORDS = {}
PLACE_COORDS.update(CHINA_CITY_COORDS)
PLACE_COORDS.update(CHINA_PROVINCE_COORDS)

_words_cache = None
_words_cache_time = 0
_words_cache_lock = False


def _jieba_cut(text):
    """jieba 分词并过滤停用词。
    
    Args:
        text: 待分词的原始文本
        
    Returns:
        过滤后的词语列表（长度>=2 且不在停用词表中）
    """
    if not text:
        return []
    text = re.sub(r'<[^>]+>', '', text or '')
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return []
    import jieba
    words = jieba.lcut(text)
    return [w.strip() for w in words if len(w.strip()) >= 2 and w.strip() not in STOP_WORDS]


def _jieba_posseg_extract_places(texts):
    if not texts:
        return []
    import jieba.posseg as pseg
    place_counter = Counter()
    for text in texts:
        if not text:
            continue
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        if not text:
            continue
        try:
            words = pseg.lcut(text)
            for word, flag in words:
                if flag == 'ns' and len(word) >= 2:
                    place_counter[word] += 1
        except Exception:
            pass
    return place_counter.most_common(100)


def _precompute_wordcloud():
    """异步后台任务 — 预计算词云数据并缓存到模块级变量。
    
    通过 tornado.ioloop.IOLoop.spawn_callback 调度，
    避免阻塞主线程。缓存有效期 10 分钟。
    """
    global _words_cache, _words_cache_time, _words_cache_lock
    if _words_cache_lock:
        return
    _words_cache_lock = True
    try:
        with get_connection() as conn:
            titles = [
                r["title"] for r in
                conn.execute("SELECT title FROM watch_data WHERE title IS NOT NULL AND title != '' ORDER BY id DESC LIMIT 2000").fetchall()
            ]
            messages = [
                r["content"] for r in
                conn.execute("SELECT content FROM im_messages WHERE content IS NOT NULL AND content != '' AND sender_id != 0 ORDER BY id DESC LIMIT 2000").fetchall()
            ]
        word_counter = Counter()
        for text in titles + messages:
            words = _jieba_cut(text)
            word_counter.update(words)
        top_words = word_counter.most_common(50)
        _words_cache = [{"name": w, "value": c} for w, c in top_words]
        _words_cache_time = time.time()
    except Exception:
        pass
    finally:
        _words_cache_lock = False


def get_cached_wordcloud():
    """获取缓存的词云数据。
    
    Returns:
        词云列表 [{"name": "词", "value": 频次}, ...] 或 None（缓存失效时）
    """
    global _words_cache, _words_cache_time
    if _words_cache and (time.time() - _words_cache_time) < 600:
        return _words_cache
    if not _words_cache_lock:
        try:
            tornado.ioloop.IOLoop.current().spawn_callback(_precompute_wordcloud)
        except Exception:
            pass
    return None


class ScreenDashboardHandler(BaseHandler):
    """大屏页面 Handler — 渲染独立全屏 dashboard 页面。
    
    路由: GET /screen/dashboard
    """
    def get(self):
        self.render("screen_dashboard.html")


class ScreenWordDetailHandler(BaseHandler):
    """关键词详情 Handler — 按关键词搜索瞭望数据标题列表。
    
    路由: GET /api/screen/word-detail?keyword=xxx
    返回: {"code":0, "msg":"", "data":[{"id":..., "title":..., "url":..., "create_at":...}]}
    """
    def get(self):
        keyword = (self.get_argument("keyword", "") or "").strip()
        if not keyword:
            self.write({"code": 1, "msg": "缺少 keyword 参数", "data": []})
            return
        try:
            with get_connection() as conn:
                rows = conn.execute(
                    "SELECT id, title, url, create_at FROM watch_data WHERE title LIKE ? ORDER BY id DESC LIMIT 50",
                    (f"%{keyword}%",)
                ).fetchall()
                data = []
                for r in rows:
                    data.append({
                        "id": r["id"],
                        "title": r["title"],
                        "url": r["url"] or "",
                        "create_at": r["create_at"],
                    })
            self.write({"code": 0, "msg": "", "data": data})
        except Exception as e:
            self.write({"code": 1, "msg": f"查询异常: {str(e)}", "data": []})


def _normalize_day_key(day_val):
    """将 DATE() 结果统一为 YYYY-MM-DD 字符串，兼容 SQLite 与 MySQL。"""
    if day_val is None:
        return None
    if hasattr(day_val, "isoformat"):
        return day_val.isoformat()
    return str(day_val)[:10]


class ScreenStatsHandler(BaseHandler):
    """统计 Handler — 返回平台关键指标与趋势数据。
    
    路由: GET /api/screen/stats
    返回: total_users, total_sessions, total_watch_data, trend_dates/values, msg_trend_values, category_stats
    """
    def get(self):
        try:
            cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            with get_connection() as conn:
                total_users = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()["cnt"]

                total_sessions = conn.execute("SELECT COUNT(*) as cnt FROM chat_sessions").fetchone()["cnt"]

                total_watch = conn.execute("SELECT COUNT(*) as cnt FROM watch_data").fetchone()["cnt"]

                rows = conn.execute(
                    """SELECT DATE(create_at) AS day, COUNT(*) AS cnt
                       FROM watch_data
                       WHERE create_at >= ?
                       GROUP BY DATE(create_at)
                       ORDER BY day""",
                    (cutoff,),
                ).fetchall()
                trend_dates = []
                trend_values = []
                msg_trend_values = []
                today = datetime.now().date()
                existing = {}
                for r in rows:
                    existing[_normalize_day_key(r["day"])] = r["cnt"]

                msg_rows = conn.execute(
                    """SELECT DATE(create_at) AS day, COUNT(*) AS cnt
                       FROM im_messages
                       WHERE sender_id != 0 AND create_at >= ?
                       GROUP BY DATE(create_at)
                       ORDER BY day""",
                    (cutoff,),
                ).fetchall()
                msg_existing = {}
                for r in msg_rows:
                    msg_existing[_normalize_day_key(r["day"])] = r["cnt"]

                for i in range(6, -1, -1):
                    d = (today - timedelta(days=i)).isoformat()
                    trend_dates.append(d)
                    trend_values.append(existing.get(d, 0))
                    msg_trend_values.append(msg_existing.get(d, 0))

                category_rows = conn.execute(
                    """SELECT msg_type, COUNT(*) as cnt
                       FROM im_messages
                       WHERE sender_id != 0
                       GROUP BY msg_type"""
                ).fetchall()
                category_stats = {}
                for r in category_rows:
                    category_stats[r["msg_type"] or "text"] = r["cnt"]

            self.write({
                "code": 0,
                "msg": "",
                "data": {
                    "total_users": total_users,
                    "total_sessions": total_sessions,
                    "total_watch_data": total_watch,
                    "trend_dates": trend_dates,
                    "trend_values": trend_values,
                    "msg_trend_values": msg_trend_values,
                    "category_stats": category_stats,
                }
            })
        except Exception as e:
            self.write({"code": 1, "msg": f"统计接口异常: {str(e)}"})


class ScreenWordcloudHandler(BaseHandler):
    """词云 Handler — 返回高频关键词及其权重。
    
    路由: GET /api/screen/wordcloud
    优先返回异步预计算的缓存数据（10分钟有效），缓存未命中时实时计算。
    
    Returns:
        [{"name": "词语", "value": 频次}, ...] 共50条
    """
    def get(self):
        try:
            cached = get_cached_wordcloud()
            if cached:
                self.write({"code": 0, "msg": "缓存命中", "data": cached})
                return
            result = self._build_wordcloud()
            self.write({"code": 0, "msg": "", "data": result})
        except Exception as e:
            self.write({"code": 1, "msg": f"词云接口异常: {str(e)}", "data": []})

    def _build_wordcloud(self):
        """从数据库拉取瞭望标题和聊天消息，分词后取 Top 50 关键词。"""
        with get_connection() as conn:
            titles = [
                r["title"] for r in
                conn.execute("SELECT title FROM watch_data WHERE title IS NOT NULL AND title != '' ORDER BY id DESC LIMIT 2000").fetchall()
            ]
            messages = [
                r["content"] for r in
                conn.execute("SELECT content FROM im_messages WHERE content IS NOT NULL AND content != '' AND sender_id != 0 ORDER BY id DESC LIMIT 2000").fetchall()
            ]
        word_counter = Counter()
        for text in titles + messages:
            words = _jieba_cut(text)
            word_counter.update(words)

        top_words = word_counter.most_common(50)
        return [{"name": w, "value": c} for w, c in top_words]


class ScreenEarthDataHandler(BaseHandler):
    """地球数据 Handler — 返回带坐标的地理位置热力数据。
    
    路由: GET /api/screen/earth-data
    使用 jieba.posseg 识别地名 (ns 词性)，匹配预置坐标库，保证至少返回5条。
    
    Returns:
        [{"name": "地名", "value": 热度, "lng": 经度, "lat": 纬度, "sentiment": 0.5}, ...]
    """
    def get(self):
        try:
            result = self._build_earth_data()
            self.write({"code": 0, "msg": "", "data": result})
        except Exception as e:
            self.write({"code": 1, "msg": f"地球数据接口异常: {str(e)}", "data": []})

    def _build_earth_data(self):
        with get_connection() as conn:
            titles = [
                r["title"] for r in
                conn.execute("SELECT title FROM watch_data WHERE title IS NOT NULL AND title != '' ORDER BY id DESC LIMIT 500").fetchall()
            ]
            contents = [
                r["content"] for r in
                conn.execute("SELECT content FROM watch_data WHERE content IS NOT NULL AND content != '' ORDER BY id DESC LIMIT 500").fetchall()
            ]

        place_counter = _jieba_posseg_extract_places(titles + contents)

        earth_data = []
        seen = set()
        for place_name, count in place_counter:
            if place_name in seen:
                continue
            coords = PLACE_COORDS.get(place_name)
            if coords:
                seen.add(place_name)
                earth_data.append({
                    "name": place_name,
                    "value": min(count * 10, 100),
                    "lng": round(coords[0], 2),
                    "lat": round(coords[1], 2),
                    "sentiment": 0.5,
                })

        default_places = [
            ("北京", (116.40, 39.90), 90),
            ("上海", (121.47, 31.23), 85),
            ("广州", (113.26, 23.13), 75),
            ("成都", (104.07, 30.67), 80),
            ("深圳", (114.07, 22.62), 70),
            ("武汉", (114.30, 30.60), 60),
            ("杭州", (120.16, 30.24), 65),
            ("重庆", (106.55, 29.57), 55),
        ]

        while len(earth_data) < 5:
            for name, (lng, lat), val in default_places:
                if name not in seen:
                    seen.add(name)
                    earth_data.append({
                        "name": name, "value": val,
                        "lng": lng, "lat": lat,
                        "sentiment": 0.5,
                    })
                    break

        return earth_data


class ScreenLocationNewsHandler(BaseHandler):
    """地点新闻 Handler — 按地理位置搜索关联的瞭望数据。
    
    路由: GET /api/screen/location-news?location=xxx
    从 watch_data 中检索标题或正文包含指定地名的条目，
    返回标题、摘要(前120字)、原文链接和时间。
    """
    def get(self):
        location = (self.get_argument("location", "") or "").strip()
        if not location:
            self.write({"code": 1, "msg": "缺少 location 参数", "data": []})
            return
        try:
            with get_connection() as conn:
                rows = conn.execute(
                    "SELECT id, title, url, content, create_at FROM watch_data WHERE (title LIKE ? OR content LIKE ?) ORDER BY id DESC LIMIT 30",
                    (f"%{location}%", f"%{location}%")
                ).fetchall()
                data = []
                for r in rows:
                    summary = (r["content"] or "")[:120]
                    data.append({
                        "id": r["id"],
                        "title": r["title"],
                        "url": r["url"] or "",
                        "summary": summary,
                        "create_at": r["create_at"],
                    })
            self.write({"code": 0, "msg": "", "data": data})
        except Exception as e:
            self.write({"code": 1, "msg": f"查询异常: {str(e)}", "data": []})


class ScreenAnalyzeHandler(BaseHandler):
    """智能分析 Handler — 对用户聊天记录进行违规检测与话题提炼。
    
    路由: POST /api/screen/analyze
    请求体: {"days": 7}
    
    流程:
        1. 查缓存 (screen_analysis_result 表, 1小时 TTL)
        2. 缓存未命中 → 拉取聊天记录 → AI模型分析 (或兜底规则)
        3. 写入缓存 + 审计日志 (screen_analysis_log 表)
    
    返回:
        {
            "risk_level": "高/中/低",
            "normal_rate": 0.0-1.0,
            "violation_rate": 0.0-1.0,
            "neutral_rate": 0.0-1.0,
            "top_violation_words": ["违规词", ...],
            "hot_topics": ["话题", ...],
            "summary": "50字以内摘要",
            "suggestion": "建议措施"
        }
    """
    def check_xsrf_cookie(self):
        pass

    async def post(self):
        t0 = time.time()
        try:
            body = json.loads(self.request.body or "{}") if self.request.body else {}
        except json.JSONDecodeError:
            body = {}
        days = body.get("days", 7)
        force = body.get("force", False)
        if not isinstance(days, int) or days < 1 or days > 365:
            days = 7

        cached = None if force else self._get_cached_result(days)
        if cached:
            elapsed = int((time.time() - t0) * 1000)
            self._write_audit_log(days, cached["risk_level"],
                                  cached.get("normal_rate", 0),
                                  cached.get("violation_rate", 0),
                                  cached.get("neutral_rate", 0),
                                  elapsed, is_cached=1)
            self.write({"code": 0, "msg": "命中缓存", "data": cached})
            return

        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(self._do_analyze, days),
                timeout=5
            )
            elapsed = int((time.time() - t0) * 1000)
            self._save_cached_result(days, result)
            self._write_audit_log(days, result["risk_level"],
                                  result.get("normal_rate", 0),
                                  result.get("violation_rate", 0),
                                  result.get("neutral_rate", 0),
                                  elapsed, is_cached=0)
            self.write({"code": 0, "msg": "", "data": result})
        except asyncio.TimeoutError:
            result = self._fallback_analyze_simple(days)
            elapsed = int((time.time() - t0) * 1000)
            self._save_cached_result(days, result)
            self._write_audit_log(days, result["risk_level"],
                                  result.get("normal_rate", 0),
                                  result.get("violation_rate", 0),
                                  result.get("neutral_rate", 0),
                                  elapsed, is_cached=0)
            self.write({"code": 0, "msg": "AI分析超时，返回基础分析结果", "data": result})
        except Exception as e:
            elapsed = int((time.time() - t0) * 1000)
            self._write_audit_log(days, "低", 0, 0, 0, elapsed, is_cached=0,
                                  error_msg=str(e))
            self.write({"code": 1, "msg": f"分析异常: {str(e)}"})

    def _get_cached_result(self, days):
        """检查缓存是否有效。
        
        缓存失效条件（满足任一即失效）：
        1. 缓存超过 5 分钟
        2. 聊天记录最新一条的 create_at 晚于缓存创建时间（有新消息）
        """
        try:
            with get_connection() as conn:
                row = conn.execute(
                    "SELECT raw_json, create_at FROM screen_analysis_result WHERE days = ? ORDER BY id DESC LIMIT 1",
                    (days,)
                ).fetchone()
                if not row:
                    return None
                created = datetime.strptime(row["create_at"], "%Y-%m-%d %H:%M:%S")
                age = (datetime.now() - created).total_seconds()
                if age > 300 or age < 0:
                    return None
                latest = conn.execute(
                    "SELECT MAX(create_at) AS latest FROM im_messages WHERE sender_id != 0"
                ).fetchone()
                if latest and latest["latest"]:
                    latest_time = datetime.strptime(latest["latest"], "%Y-%m-%d %H:%M:%S")
                    if latest_time > created:
                        return None
                if row["raw_json"]:
                    return json.loads(row["raw_json"])
        except Exception:
            pass
        return None

    def _save_cached_result(self, days, result):
        try:
            with get_connection() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO screen_analysis_result
                       (days, risk_level, normal_rate, violation_rate, neutral_rate,
                        top_violation_words, hot_topics, summary, suggestion, raw_json, create_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,datetime('now'))""",
                    (
                        days,
                        result.get("risk_level", "低"),
                        result.get("normal_rate", 0),
                        result.get("violation_rate", 0),
                        result.get("neutral_rate", 0),
                        json.dumps(result.get("top_violation_words", []), ensure_ascii=False),
                        json.dumps(result.get("hot_topics", []), ensure_ascii=False),
                        result.get("summary", "")[:50],
                        result.get("suggestion", ""),
                        json.dumps(result, ensure_ascii=False),
                    )
                )
                conn.commit()
        except Exception:
            pass

    def _write_audit_log(self, days, risk_level, normal_rate, violation_rate,
                         neutral_rate, elapsed_ms, is_cached=0, error_msg=""):
        try:
            with get_connection() as conn:
                conn.execute(
                    """INSERT INTO screen_analysis_log
                       (days, risk_level, normal_rate, violation_rate, neutral_rate,
                        elapsed_ms, is_cached, error_msg, create_at)
                       VALUES(?,?,?,?,?,?,?,?,datetime('now'))""",
                    (days, risk_level, normal_rate, violation_rate, neutral_rate,
                     elapsed_ms, is_cached, error_msg)
                )
                conn.commit()
        except Exception:
            pass

    def _do_analyze(self, days):
        since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        with get_connection() as conn:
            chat_rows = conn.execute(
                """SELECT content FROM im_messages
                   WHERE create_at >= ? AND sender_id != 0 AND content IS NOT NULL AND content != ''
                   ORDER BY id DESC LIMIT 500""",
                (since_date,)
            ).fetchall()

        chat_texts = [r["content"][:300] for r in chat_rows if r["content"]]

        if not chat_texts:
            return {
                "risk_level": "低",
                "normal_rate": 1.0,
                "violation_rate": 0.0,
                "neutral_rate": 0.0,
                "top_violation_words": [],
                "hot_topics": [],
                "summary": f"最近{days}天暂无用户聊天记录",
                "suggestion": "暂无聊天数据，无需特别处理。",
            }

        combined_text = "\n---\n".join(chat_texts[:200])

        violation_keywords = self._extract_violation_keywords(combined_text)
        hot_topics = self._extract_hot_topics(chat_texts)

        model = ModelEngineRepository.get_default()
        if model:
            ai_result = self._call_ai_analyze_with_timeout(model, combined_text, days, timeout=3)
            if ai_result:
                ai_result["top_violation_words"] = (
                    ai_result.get("top_violation_words") or violation_keywords[:5]
                )
                ai_result["hot_topics"] = hot_topics
                return ai_result

        return self._fallback_analyze(chat_texts, days, violation_keywords, hot_topics)

    def _fallback_analyze_simple(self, days):
        since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with get_connection() as conn:
            chat_rows = conn.execute(
                "SELECT content FROM im_messages WHERE create_at >= ? AND sender_id != 0 AND content IS NOT NULL AND content != '' ORDER BY id DESC LIMIT 500",
                (since_date,)
            ).fetchall()
        chat_texts = [r["content"][:300] for r in chat_rows if r["content"]]
        combined_text = "\n".join(chat_texts[:100])
        violation_keywords = self._extract_violation_keywords(combined_text)
        hot_topics = self._extract_hot_topics(chat_texts)
        return self._fallback_analyze(chat_texts, days, violation_keywords, hot_topics)

    def _call_ai_analyze_with_timeout(self, model, combined_text, days, timeout):
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._call_ai_analyze, model, combined_text, days)
            try:
                return future.result(timeout=timeout)
            except FuturesTimeoutError:
                return None
            except Exception:
                return None

    def _call_ai_analyze(self, model, combined_text, days):
        try:
            prompt = f"""你是一个聊天内容审核师。请分析以下最近{days}天的用户聊天记录，检测是否存在违规内容，并提炼用户讨论的热门话题。

违规内容包括但不限于：色情、暴力、赌博、诈骗、毒品、政治敏感、人身攻击、恶意骚扰、传播谣言、非法交易等。

请严格按以下 JSON 格式返回结果（不要输出其他内容）：
{{"risk_level":"高/中/低","normal_rate":0.0-1.0,"violation_rate":0.0-1.0,"neutral_rate":0.0-1.0,"top_violation_words":["违规词1","违规词2"],"summary":"用户聊天简要概括，不超过50字","suggestion":"针对风险情况的建议措施，不超过50字"}}

注意：
- risk_level：存在明确违规内容为"高"，有擦边嫌疑为"中"，正常聊天为"低"
- normal_rate：正常对话占比
- violation_rate：违规内容占比
- neutral_rate：中性/无法判断内容占比
- top_violation_words：检测到的违规关键词或敏感词
- summary：简要概括用户聊天话题，不得超过50字，如有违规需明确指出
- suggestion：针对当前风险等级给出管理建议措施，不得超过50字

聊天记录：
{combined_text[:8000]}
"""

            from openai import OpenAI
            import httpx
            client = OpenAI(
                api_key=model.get("api_key") or "sk-no-key-required",
                base_url=model.get("base_url") or "https://api.openai.com/v1",
                http_client=httpx.Client(timeout=httpx.Timeout(3.0, connect=2.0)),
            )
            resp = client.chat.completions.create(
                model=model.get("model_name") or "gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=min(model.get("max_tokens", 2048), 1024),
                temperature=0.3,
            )
            reply = resp.choices[0].message.content.strip()

            json_match = re.search(r'\{[\s\S]*\}', reply)
            if json_match:
                result = json.loads(json_match.group(0))
                required_keys = ["risk_level", "normal_rate", "violation_rate", "neutral_rate", "top_violation_words", "summary", "suggestion"]
                for k in required_keys:
                    if k not in result:
                        return None
                return result
        except Exception:
            return None
        return None

    def _extract_violation_keywords(self, text):
        violation_words = {
            "草", "操", "他妈", "fuck", "妈的", "日", "靠", "傻逼", "脑残",
            "色情", "色图", "裸聊", "约炮", "嫖娼", "妓女", "招嫖",
            "赌博", "赌场", "博彩", "下注", "赌球", "六合彩",
            "诈骗", "骗钱", "套路", "坑人", "传销", "杀猪盘",
            "毒品", "吸毒", "大麻", "海洛因", "冰毒", "摇头丸",
            "暴力", "打死", "砍死", "弄死", "杀人", "行凶",
            "枪支", "手枪", "炸弹", "炸药", "恐怖",
            "翻墙", "vpn", "反动", "颠覆", "煽动",
            "谣言", "造谣", "虚假", "传谣",
            "骚扰", "骂人", "侮辱", "人身攻击",
            "黑客", "盗号", "窃取", "破解",
            "自杀", "自残", "割腕", "跳楼",
            "人肉", "曝光", "隐私", "泄露",
        }
        words = _jieba_cut(text)
        matched = [w for w in words if w in violation_words]
        counter = Counter(matched)
        return [w for w, _ in counter.most_common(10)]

    def _extract_hot_topics(self, chat_texts):
        all_words = []
        for t in chat_texts:
            all_words.extend(_jieba_cut(t))
        topic_counter = Counter(all_words)
        topic_words = [
            w for w, _ in topic_counter.most_common(30)
            if len(w) >= 2 and w not in {
                "什么", "怎么", "这个", "那个", "一个", "可以", "没有",
                "不是", "就是", "还是", "我们", "他们", "自己", "因为",
                "所以", "但是", "如果", "虽然", "而且", "不过", "然后",
                "已经", "可能", "应该", "需要", "就是", "知道", "觉得",
                "问题", "大家", "一下", "一点", "现在", "真的", "感觉",
                "事情", "比较", "不同", "一样", "非常", "特别",
                "吗", "呢", "啊", "吧", "嗯", "哦",
            }
        ]
        return topic_words[:10]

    def _fallback_analyze(self, chat_texts, days, violation_keywords, hot_topics):
        all_words = []
        for t in chat_texts:
            all_words.extend(_jieba_cut(t))

        normal_indicator_words = {
            "你好", "谢谢", "请问", "帮忙", "有没有", "能不能",
            "怎么", "什么", "哪里", "哪个", "多少钱", "价格",
            "介绍", "推荐", "使用", "设置", "功能", "问题",
            "学习", "工作", "生活", "吃饭", "睡觉", "天气",
            "电影", "音乐", "游戏", "手机", "电脑", "旅游",
            "你好呀", "好的", "嗯嗯", "哈哈", "可以", "谢谢啦",
        }
        violation_indicator_words = {
            "草", "操", "傻逼", "脑残", "他妈", "妈的", "日", "靠",
            "fuck", "色情", "色图", "裸聊", "约炮", "嫖娼", "妓女", "招嫖",
            "赌博", "诈骗", "毒品", "暴力", "赌场", "博彩", "吸毒", "大麻",
            "杀", "死", "骗", "偷", "抢", "嫖", "赌", "毒",
            "翻墙", "vpn", "造反", "骂人", "举报", "曝光",
            "自杀", "跳楼", "割腕", "砍人", "打人", "杀人",
            "黑客", "盗号", "破解", "窃取",
        }

        total = len(all_words)
        normal_count = sum(1 for w in all_words if w in normal_indicator_words)
        violation_count = sum(1 for w in all_words if w in violation_indicator_words)
        neutral_count = total - normal_count - violation_count

        if total > 0:
            normal_rate = round(normal_count / total, 2)
            violation_rate = round(violation_count / total, 2)
            neutral_rate = round(max(neutral_count / total, 0), 2)
        else:
            normal_rate = 0.0
            violation_rate = 0.0
            neutral_rate = 1.0

        if violation_rate > 0.15:
            risk_level = "高"
        elif violation_rate > 0.03:
            risk_level = "中"
        else:
            risk_level = "低"

        if not violation_keywords:
            violation_counter = Counter([w for w in all_words if w in violation_indicator_words])
            violation_keywords = [w for w, _ in violation_counter.most_common(5)]

        summary = f"最近{days}天共分析{len(chat_texts)}条用户消息"
        suggestion = ""
        if risk_level == "低":
            summary += "，未发现明显违规内容，聊天氛围正常。"
            suggestion = "当前聊天环境安全，继续保持日常巡检即可。"
        elif risk_level == "中":
            summary += "，存在少量疑似违规或敏感内容，建议关注。"
            suggestion = "建议对相关涉事用户进行重点观察，必要时可警告处理。"
        else:
            summary += "，检测到较多违规/敏感内容，建议立即审查处理。"
            suggestion = "建议立即启动违规内容清理，对涉事账号做封禁处理并追溯。"
        summary = summary[:50]

        if hot_topics:
            summary += f" 热门话题：{'、'.join(hot_topics[:5])}。"

        return {
            "risk_level": risk_level,
            "normal_rate": normal_rate,
            "violation_rate": violation_rate,
            "neutral_rate": neutral_rate,
            "top_violation_words": violation_keywords[:5],
            "hot_topics": hot_topics,
            "summary": summary,
            "suggestion": suggestion,
        }
