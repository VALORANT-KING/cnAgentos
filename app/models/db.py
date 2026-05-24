# 数据库链接与建表
import os
import sqlite3

# 获得项目根路径的方法
def _project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
#获得数据文件的路径
DB_PATH = os.path.join(_project_root(),"database","app.db")

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH),exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users(
                id integer PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                status INTEGER NOT NULL DEFAULT 1,
                create_at TEXT NOT NULL DEFAULT(datetime('now'))
            )
            """
        )
        try:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
            conn.execute("ALTER TABLE users ADD COLUMN status INTEGER NOT NULL DEFAULT 1")
            conn.commit()
        except Exception:
            pass

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS modules(
                id integer PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                icon TEXT DEFAULT '',
                url TEXT DEFAULT '',
                parent_id INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                status INTEGER NOT NULL DEFAULT 1,
                create_at TEXT NOT NULL DEFAULT(datetime('now'))
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS roles(
                id integer PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT '',
                is_system INTEGER NOT NULL DEFAULT 0,
                status INTEGER NOT NULL DEFAULT 1,
                create_at TEXT NOT NULL DEFAULT(datetime('now'))
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS role_permissions(
                id integer PRIMARY KEY AUTOINCREMENT,
                role_id INTEGER NOT NULL,
                module_id INTEGER NOT NULL,
                create_at TEXT NOT NULL DEFAULT(datetime('now'))
            )
            """
        )

        try:
            cursor = conn.execute("SELECT id FROM modules LIMIT 1")
            if not cursor.fetchone():
                conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("系统管理", "layui-icon-home", "", 0, 1))
                conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("系统首页", "layui-icon-app", "/admin/home", 1, 1))
                conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("用户管理", "layui-icon-username", "/admin/user/manage", 1, 2))
                conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("功能管理", "layui-icon-template-1", "/admin/module/manage", 1, 3))
                conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("权限管理", "layui-icon-vercode", "/admin/permission/manage", 1, 4))
                conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("角色管理", "layui-icon-user", "/admin/role/manage", 1, 5))
                conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("模型引擎", "layui-icon-engine", "", 0, 2))
                conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("模型配置", "layui-icon-set", "/admin/model/manage", 7, 1))
                conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("数字员工", "layui-icon-user", "", 0, 3))
                conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("员工管理", "layui-icon-group", "", 9, 1))
                conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("瞭望管理", "layui-icon-tabs", "", 0, 4))
                conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("瞭望源管理", "layui-icon-link", "/admin/watch/source", 11, 1))
                conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("采集任务", "layui-icon-log", "/admin/watch/collect", 11, 2))
                conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("数据仓库", "layui-icon-table", "", 0, 5))
                conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("数据管理", "layui-icon-file", "/admin/watch/data", 14, 1))
                conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("数智大屏", "layui-icon-chart-screen", "", 0, 6))
                conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("大屏展示", "layui-icon-template-1", "", 16, 1))
                conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("系统设置", "layui-icon-set", "", 0, 7))
                conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("系统参数", "layui-icon-set-fill", "", 18, 1))
                conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("系统统计", "layui-icon-chart", "", 18, 2))
                # 任务六：接口管理模块
                conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("接口管理", "layui-icon-list", "", 0, 8))
                conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("接口列表", "layui-icon-template-1", "/admin/api/manage", 20, 1))
                # 任务七：员工配置子菜单 (父级数字员工 id=9 已在上面第9行插入)
                conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("员工配置", "layui-icon-user", "/admin/employee/manage", 9, 1))
                conn.commit()
        except Exception:
            pass

        # 确保瞭望管理模块的 URL 正确
        try:
            with get_connection() as conn:
                conn.execute("UPDATE modules SET url = '/admin/watch/source' WHERE name = '瞭望源管理' AND (url = '' OR url IS NULL)")
                conn.execute("UPDATE modules SET url = '/admin/watch/collect' WHERE name = '采集任务' AND (url = '' OR url IS NULL)")
                conn.execute("UPDATE modules SET url = '/admin/watch/data' WHERE name = '数据管理' AND (url = '' OR url IS NULL)")
                conn.commit()
        except Exception:
            pass

        # 确保接口管理模块的内容存在
        try:
            with get_connection() as conn:
                conn.execute("UPDATE modules SET url = '/admin/api/manage' WHERE name = '接口列表' AND (url = '' OR url IS NULL)")
                conn.commit()
        except Exception:
            pass

        # 确保接口管理模块存在 (已存在数据库的情况)
        try:
            with get_connection() as conn:
                existing = conn.execute("SELECT id FROM modules WHERE name = '接口管理'").fetchone()
                if not existing:
                    conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("接口管理", "layui-icon-list", "", 0, 8))
                    pkid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("接口列表", "layui-icon-template-1", "/admin/api/manage", pkid, 1))
                    conn.commit()
        except Exception:
            pass

        # 确保数字员工模块存在 (已存在数据库的情况)
        try:
            with get_connection() as conn:
                existing = conn.execute("SELECT id FROM modules WHERE name = '员工配置'").fetchone()
                if not existing:
                    # 检查父级"数字员工"是否存在，不存在则创建
                    parent = conn.execute("SELECT id FROM modules WHERE name = '数字员工'").fetchone()
                    if not parent:
                        conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("数字员工", "layui-icon-user", "", 0, 3))
                        parent_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    else:
                        parent_id = parent["id"]
                    conn.execute("INSERT INTO modules(name, icon, url, parent_id, sort_order) VALUES(?,?,?,?,?)", ("员工配置", "layui-icon-user", "/admin/employee/manage", parent_id, 1))
                    conn.commit()
        except Exception:
            pass

        # 确保数字员工模块的 URL 正确 (针对已存在但 URL 为空的情况)
        try:
            with get_connection() as conn:
                conn.execute("UPDATE modules SET url = '/admin/employee/manage' WHERE name = '员工配置' AND (url = '' OR url IS NULL)")
                conn.commit()
        except Exception:
            pass

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS model_engines(
                id integer PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                provider TEXT DEFAULT 'openai',
                base_url TEXT DEFAULT '',
                api_key TEXT DEFAULT '',
                model_name TEXT DEFAULT '',
                type TEXT DEFAULT 'remote',
                is_default INTEGER NOT NULL DEFAULT 0,
                max_tokens INTEGER DEFAULT 2048,
                temperature REAL DEFAULT 0.7,
                status INTEGER NOT NULL DEFAULT 1,
                total_tokens INTEGER DEFAULT 0,
                request_count INTEGER DEFAULT 0,
                description TEXT DEFAULT '',
                create_at TEXT NOT NULL DEFAULT(datetime('now'))
            )
            """
        )
        try:
            conn.execute("ALTER TABLE model_engines ADD COLUMN total_tokens INTEGER DEFAULT 0")
            conn.execute("ALTER TABLE model_engines ADD COLUMN request_count INTEGER DEFAULT 0")
            conn.commit()
        except Exception:
            pass

        try:
            cursor = conn.execute("SELECT id FROM model_engines LIMIT 1")
            if not cursor.fetchone():
                conn.execute(
                    "INSERT INTO model_engines(name, provider, base_url, model_name, type, is_default, description) VALUES(?,?,?,?,?,?,?)",
                    ("GPT-3.5 Turbo", "openai", "https://api.openai.com/v1", "gpt-3.5-turbo", "remote", 1, "OpenAI GPT-3.5 Turbo 模型，默认系统模型")
                )
                conn.execute(
                    "INSERT INTO model_engines(name, provider, base_url, model_name, type, description) VALUES(?,?,?,?,?,?)",
                    ("本地Qwen模型", "local", "http://127.0.0.1:8000/v1", "qwen2.5-7b-instruct", "local", "本地部署的 Qwen2.5 7B 模型")
                )
                conn.commit()
        except Exception:
            pass

        except Exception:
            pass

        # 确保超级管理员拥有所有模块权限
        try:
            with get_connection() as conn:
                role = conn.execute("SELECT id FROM roles WHERE name = ?", ("超级管理员",)).fetchone()
                if role:
                    role_id = role["id"]
                    modules = conn.execute("SELECT id FROM modules").fetchall()
                    for m in modules:
                        # 检查权限是否已存在
                        exists = conn.execute("SELECT id FROM role_permissions WHERE role_id = ? AND module_id = ?", (role_id, m["id"])).fetchone()
                        if not exists:
                            conn.execute("INSERT INTO role_permissions(role_id, module_id) VALUES(?,?)", (role_id, m["id"]))
                    conn.commit()
        except Exception:
            pass

        # 瞭望管理相关表
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS watch_sources(
                id integer PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url_pattern TEXT NOT NULL,
                headers TEXT,
                params TEXT,
                status INTEGER NOT NULL DEFAULT 1,
                create_at TEXT NOT NULL DEFAULT(datetime('now'))
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS watch_data(
                id integer PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER,
                keyword TEXT,
                title TEXT,
                content TEXT,
                url TEXT,
                publish_time TEXT,
                create_at TEXT NOT NULL DEFAULT(datetime('now')),
                FOREIGN KEY (source_id) REFERENCES watch_sources(id)
            )
            """
        )

        # 任务六：接口管理表
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_services(
                id integer PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                method TEXT DEFAULT 'GET',
                resp_format TEXT DEFAULT 'JSON',
                qps_limit INTEGER DEFAULT 0,
                token TEXT DEFAULT '',
                status INTEGER NOT NULL DEFAULT 1,
                description TEXT DEFAULT '',
                create_at TEXT NOT NULL DEFAULT(datetime('now'))
            )
            """
        )

        # 任务六-1：插入示例 API 数据
        try:
            cursor = conn.execute("SELECT id FROM api_services LIMIT 1")
            if not cursor.fetchone():
                conn.execute(
                    "INSERT INTO api_services (name, url, method, resp_format, qps_limit, token, status, description) VALUES (?,?,?,?,?,?,?,?)",
                    ("随机音乐", "https://api.52vmy.cn/api/music/wy/rand", "GET", "JSON", 4, "", 1, "网易云随机音乐推荐，携带Token可无视QPS限制")
                )
                conn.execute(
                    "INSERT INTO api_services (name, url, method, resp_format, qps_limit, token, status, description) VALUES (?,?,?,?,?,?,?,?)",
                    ("三日天气", "https://api.52vmy.cn/api/query/tian", "GET", "JSON", 4, "", 1, "三日天气预报，参数: city=城市名，携带Token可无视QPS限制")
                )
                conn.commit()
        except Exception:
            pass

        # 任务七：数字员工表
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS digital_employees(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                alias TEXT NOT NULL UNIQUE,
                category TEXT DEFAULT 'AI',
                agent_type TEXT DEFAULT 'chat',
                api_service_id INTEGER DEFAULT 0,
                prompt TEXT DEFAULT '',
                icon TEXT DEFAULT 'fa-robot',
                description TEXT DEFAULT '',
                sort_order INTEGER DEFAULT 0,
                status INTEGER NOT NULL DEFAULT 1,
                create_at TEXT NOT NULL DEFAULT(datetime('now'))
            )
            """
        )

        # 任务七：插入初始数字员工数据
        try:
            cursor = conn.execute("SELECT id FROM digital_employees LIMIT 1")
            if not cursor.fetchone():
                conn.execute(
                    "INSERT INTO digital_employees(name, alias, category, agent_type, prompt, icon, description, sort_order) VALUES(?,?,?,?,?,?,?,?)",
                    ("川小农", "@川小农", "AI", "chat",
                     "你是川小农，四川农业大学的智能助手。你擅长回答关于四川农业大学的问题，包括校园信息、专业介绍、招生政策、校园文化等。请用热情亲切的语气回答用户的问题。",
                     "fa-leaf", "四川农业大学智能助手，回答校园相关问题", 1)
                )
                weather_id = conn.execute("SELECT id FROM api_services WHERE name = '三日天气'").fetchone()
                music_id = conn.execute("SELECT id FROM api_services WHERE name = '随机音乐'").fetchone()
                w_id = weather_id["id"] if weather_id else 0
                m_id = music_id["id"] if music_id else 0
                conn.execute(
                    "INSERT INTO digital_employees(name, alias, category, agent_type, api_service_id, icon, description, sort_order) VALUES(?,?,?,?,?,?,?,?)",
                    ("天气", "@天气", "普通", "api", w_id, "fa-cloud-sun", "查询三日天气预报，输入城市名即可", 2)
                )
                conn.execute(
                    "INSERT INTO digital_employees(name, alias, category, agent_type, api_service_id, icon, description, sort_order) VALUES(?,?,?,?,?,?,?,?)",
                    ("音乐", "@音乐", "普通", "api", m_id, "fa-music", "随机推荐网易云音乐歌曲", 3)
                )
                conn.commit()
        except Exception:
            pass

        # 任务八：对话会话表
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_sessions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT DEFAULT '新对话',
                model_id INTEGER DEFAULT 0,
                create_at TEXT NOT NULL DEFAULT(datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        # 任务八：对话消息表
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                msg_type TEXT DEFAULT 'text',
                employee_id INTEGER DEFAULT 0,
                create_at TEXT NOT NULL DEFAULT(datetime('now')),
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
            )
            """
        )

        try:
            cursor = conn.execute("SELECT id FROM watch_sources WHERE name = '百度新闻' LIMIT 1")
            import json
            baidu_headers = {
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "accept-encoding": "gzip, deflate",
                "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
                "cache-control": "max-age=0",
                "connection": "keep-alive",
                "cookie": "BAIDUID_BFESS=2D5DF11BFE8FD7F485DADDA108B0D52C:FG=1; __bid_n=197ae76c13b11527b51c2e; BIDUPSID=2D5DF11BFE8FD7F485DADDA108B0D52C; PSTM=1755759733; ploganondeg=1; BDUSS=WUtU3JPaGh4YkVzbnU2OHBPSmYyRTZkR2Z6cXZOUmFwbjB5NDJ1NGtFRDFMRlZwSVFBQUFBJCQAAAAAAQAAAAEAAADJKYqAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPWfLWn1ny1pM; BDUSS_BFESS=WUtU3JPaGh4YkVzbnU2OHBPSmYyRTZkR2Z6cXZOUmFwbjB5NDJ1NGtFRDFMRlZwSVFBQUFBJCQAAAAAAQAAAAEAAADJKYqAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPWfLWn1ny1pM; BAIDU_WISE_UID=wapp_1768614684961_842; ZFY=ghxZlrnonNSZXpkV2nfyD:ByQzc2tYu68Sx0BAzDc1fw:C; BD_UPN=12314753; BA_HECTOR=848l01012hag250l0la1052ga085ah1l14kdb29; H_WISE_SIDS=63145_67862_68166_69000_69204_69372_69591_69677_69779_69800_69921_69896_69941_69948_69961_70051_70092_70116_70151_70133_70155_70237_70261_70243_70193_70204_68739_70322_70142_70358_70390_70420_70437_70467_70475_70472_70479; BDRCVFR[feWj1Vr5u3D]=I67x6TjHwwYf0; BD_CK_SAM=1; PSINO=2; delPer=0; H_PS_645EC=4e83vGIwyoWF8uWnzIWaQTh62TDO%2FC%2BPlDdNB6A2HXg1C0%2BnJYp7a7xFBcxuL94z4ego; BDORZ=B490B5EBF6F3CD402E515D22BCDA1598; BDRCVFR[C0p6oIjvx-c]=mbxnW11j9Dfmh7GuZR8mvqV; H_PS_PSSID=63145_67862_68166_69000_69204_69372_69591_69677_69779_69800_69921_69896_69941_69948_69961_70051_70092_70116_70151_70133_70155_70237_70261_70243_70193_70204_68739_70322_70142_70358_70390_70420_70437_70467_70475_70472_70479; arialoadData=false; BDSVRTM=490",
                "host": "www.baidu.com",
                "referer": "https://news.baidu.com/",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0"
            }
            url_pattern = "https://www.baidu.com/s?rtt=1&bsst=1&cl=2&tn=news&rsv_dl=ns_pc&word={关键词}&pn={分页}"
            
            row = cursor.fetchone()
            if not row:
                conn.execute(
                    "INSERT INTO watch_sources(name, url_pattern, headers) VALUES(?,?,?)",
                    ("百度新闻", url_pattern, json.dumps(baidu_headers))
                )
            else:
                # 强制更新一下，确保配置最新
                conn.execute(
                    "UPDATE watch_sources SET url_pattern = ?, headers = ? WHERE name = ?",
                    (url_pattern, json.dumps(baidu_headers), "百度新闻")
                )
            conn.commit()
        except Exception:
            pass

        # 团队任务2：即时通信表
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS im_friends(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                friend_id INTEGER NOT NULL,
                remark TEXT DEFAULT '',
                status INTEGER DEFAULT 1,
                create_at TEXT NOT NULL DEFAULT(datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS im_friend_requests(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user_id INTEGER NOT NULL,
                to_user_id INTEGER NOT NULL,
                message TEXT DEFAULT '',
                status INTEGER DEFAULT 0,
                create_at TEXT NOT NULL DEFAULT(datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS im_groups(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                owner_id INTEGER NOT NULL,
                announcement TEXT DEFAULT '',
                status INTEGER DEFAULT 1,
                create_at TEXT NOT NULL DEFAULT(datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS im_group_members(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT DEFAULT 'member',
                create_at TEXT NOT NULL DEFAULT(datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS im_messages(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                msg_type TEXT DEFAULT 'text',
                content TEXT,
                file_path TEXT DEFAULT '',
                file_id INTEGER DEFAULT 0,
                sender_id INTEGER NOT NULL,
                receiver_type TEXT NOT NULL,
                receiver_id INTEGER NOT NULL,
                employee_id INTEGER DEFAULT 0,
                create_at TEXT NOT NULL DEFAULT(datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS im_files(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                file_hash TEXT DEFAULT '',
                uploader_id INTEGER NOT NULL,
                create_at TEXT NOT NULL DEFAULT(datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS im_servers(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                host TEXT NOT NULL,
                port INTEGER DEFAULT 10086,
                status INTEGER DEFAULT 1,
                current_load INTEGER DEFAULT 0,
                create_at TEXT NOT NULL DEFAULT(datetime('now'))
            )
            """
        )
        try:
            cursor = conn.execute("SELECT id FROM im_servers LIMIT 1")
            if not cursor.fetchone():
                conn.execute(
                    "INSERT INTO im_servers(name, host, port, status) VALUES(?,?,?,?)",
                    ("本机服务", "127.0.0.1", 10086, 1)
                )
                conn.commit()
        except Exception:
            pass

        try:
            cursor = conn.execute("SELECT id FROM roles LIMIT 1")
            if not cursor.fetchone():
                conn.execute("INSERT INTO roles(name, description, is_system) VALUES(?,?,?)", ("超级管理员", "系统默认超级管理员，拥有所有权限", 1))
                conn.execute("INSERT INTO roles(name, description, is_system) VALUES(?,?,?)", ("普通管理员", "普通管理员角色", 0))
                conn.commit()
                role_id = conn.execute("SELECT id FROM roles WHERE name = ?", ("超级管理员",)).fetchone()["id"]
                modules = conn.execute("SELECT id FROM modules").fetchall()
                for m in modules:
                    conn.execute("INSERT INTO role_permissions(role_id, module_id) VALUES(?,?)", (role_id, m["id"]))
                conn.commit()
        except Exception:
            pass