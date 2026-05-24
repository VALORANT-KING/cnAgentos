# AI 智能瞭望与智能问数系统 — 团队开发需求文档

> **版本**: 3.0 | **最后更新**: 2026-05-24 | **状态**: 定稿

---

## 目录

- [一、项目概述](#一项目概述)
- [二、项目结构与命名规范](#二项目结构与命名规范)
- [三、数据库表结构（完整）](#三数据库表结构完整)
- [四、API 路由规范（完整路由表）](#四api-路由规范完整路由表)
- [五、任务分解与详细需求](#五任务分解与详细需求)
  - [任务一：后台框架 + 管理登录（已完成）](#任务一后台框架--管理登录已完成)
  - [任务二：用户管理（已完成）](#任务二用户管理已完成)
  - [任务三：模块·权限·角色管理（已完成）](#任务三模块权限角色管理已完成)
  - [任务四：模型引擎（已完成）](#任务四模型引擎已完成)
  - [任务五：瞭望管理（已完成）](#任务五瞭望管理已完成)
  - [任务六：接口管理（已完成）](#任务六接口管理已完成)
  - [任务七：数字员工管理](#任务七数字员工管理)
  - [任务八：前端用户侧（登录·注册·问数）](#任务八前端用户侧登录注册问数)
  - [团队任务 1：功能完整性](#团队任务-1功能完整性)
  - [团队任务 2：仿微信即时通信子系统](#团队任务-2仿微信即时通信子系统)
  - [团队任务 3：智慧舆情](#团队任务-3智慧舆情)
  - [团队任务 4：视觉/语音功能增强](#团队任务-4视觉语音功能增强)
  - [团队任务 5：多数据库支持](#团队任务-5多数据库支持)
- [六、开发规范（团队强制执行）](#六开发规范团队强制执行)
- [七、提交规范（Commit Convention）](#七提交规范commit-convention)
- [八、分支策略](#八分支策略)
- [九、需求状态看板](#九需求状态看板)

---

## 一、项目概述

### 1.1 项目背景

基于 **Tornado MVC** 架构的 B/S 系统，集成了 AI 大模型对话、智能数据采集（瞭望）、互联网 API 接口集中管理、数字员工调度及用户侧智能问数等功能。后期将扩展为仿微信即时通信、智慧舆情分析、视觉/语音交互、多数据库支持的企业级平台。

### 1.2 技术栈

| 层级 | 技术选型 | 版本/说明 |
|------|----------|----------|
| 后端框架 | Tornado | 6.5.5（异步 MVC） |
| 数据库 | SQLite3 | 文件 `database/app.db`，后期扩展 MySQL |
| 数据访问 | 原生 sqlite3 | 手写 Repository 模式，参数化查询防注入 |
| AI SDK | OpenAI Python SDK | 2.38.0（兼容任意 OpenAI 范式 API） |
| 管理侧 UI | Layui | 2.13.6（界定符 `[[ ]]`） |
| 用户侧 UI | Bootstrap 5.3 + FontAwesome 5.15 | 响应式布局 |
| 图标库 | FontAwesome 5.15 | 本地化部署 |
| 爬虫引擎 | Requests + BeautifulSoup4 | Session 维持 + 多级解析 |
| Python | 3.12+ | 兼容 3.13 |
| 即时通信（团队2） | WebSocket | Tornado 原生支持 |
| 可视化（团队3） | Echarts + Echarts-GL | 词云 + 3D 地球 |

### 1.3 核心约束

| 序号 | 约束 | 说明 |
|------|------|------|
| 1 | 禁止 CDN | 所有静态资源本地化存放于 `app/static/dist/` |
| 2 | XSRF 防护 | 所有 POST/AJAX 必须携带 `_xsrf` 令牌 |
| 3 | 架构模式 | Tornado MVC，管理侧 左菜单+右 iframe |
| 4 | 爬虫规范 | `requests.Session` + `verify=False`，禁用 br/zstd |
| 5 | 数据库安全 | 统一参数化查询，禁止字符串拼接 SQL |
| 6 | 解析策略 | JSON提取 → DOM解析 → 正则兜底（三层保险） |
| 7 | 错误处理 | 所有异常捕获返回 JSON，避免前端网络错误 |

---

## 二、项目结构与命名规范

### 2.1 最终项目目录结构

```
cnAgentos/
│
├── app.py                          # 主入口 + 路由注册表
├── .gitignore
├── README.md
├── requirements.txt                # Python 依赖清单
├── requirements.md                 # 本需求文档（团队开发依据）
│
├── database/
│   └── app.db                      # SQLite 数据库文件
│
├── app/
│   ├── __init__.py
│   │
│   ├── controllers/                # ▸ MVC-Controller 层
│   │   ├── __init__.py
│   │   ├── base.py                 #   BaseHandler（所有 Handler 基类）
│   │   ├── auth.py                 #   用户侧认证（登录/登出/注册）
│   │   ├── home.py                 #   用户侧首页
│   │   ├── chat.py                 #   【任务八】用户侧问数（对话/SSE）
│   │   ├── im.py                   #   【团队2】即时通信（WebSocket）
│   │   └── admin.py                #   管理侧所有 Handler
│   │
│   ├── models/                     # ▸ MVC-Model 层
│   │   ├── __init__.py
│   │   ├── db.py                   #   数据库连接 + 建表 + 初始化数据
│   │   ├── user.py                 #   用户 CRUD
│   │   ├── module.py               #   功能模块 CRUD
│   │   ├── role.py                 #   角色 CRUD
│   │   ├── model_engine.py         #   模型引擎 CRUD
│   │   ├── watch.py                #   瞭望源 + 数据仓库 CRUD
│   │   ├── api_service.py          #   接口管理 CRUD【任务六】
│   │   ├── digital_employee.py     #   数字员工 CRUD【任务七】
│   │   ├── chat_session.py         #   【任务八】对话会话 CRUD
│   │   ├── chat_message.py         #   【任务八】对话消息 CRUD
│   │   ├── im_friend.py            #   【团队2】好友关系 CRUD
│   │   ├── im_group.py             #   【团队2】群组 CRUD
│   │   ├── im_message.py           #   【团队2】聊天消息 CRUD
│   │   ├── im_file.py              #   【团队2】文件管理 CRUD
│   │   └── db_config.py            #   【团队5】多数据库配置 CRUD
│   │
│   ├── templates/                  # ▸ MVC-View 层（Tornado 模板）
│   │   │
│   │   ├── base.html               #   用户侧基础布局
│   │   ├── index.html              #   用户侧首页
│   │   ├── login.html              #   用户登录
│   │   ├── register.html           #   用户注册
│   │   ├── chat.html               #   【任务八】问数对话界面
│   │   │
│   │   ├── admin_index.html        #   管理侧框架（左菜单右 iframe）
│   │   ├── admin_login.html        #   管理登录
│   │   ├── admin_home.html         #   管理首页
│   │   ├── admin_user_manage.html  #   用户管理
│   │   ├── admin_module_manage.html#   功能模块管理
│   │   ├── admin_role_manage.html  #   角色管理
│   │   ├── admin_permission_manage.html # 权限管理
│   │   ├── admin_model_manage.html #   模型引擎
│   │   ├── admin_watch_source.html #   瞭望源管理
│   │   ├── admin_watch_collect.html#   采集任务
│   │   ├── admin_watch_data.html   #   数据仓库
│   │   ├── admin_api_manage.html   #   接口管理【任务六】
│   │   ├── admin_employee_manage.html # 数字员工【任务七】
│   │   │
│   │   ├── im_index.html           #   【团队2】即时通信首页
│   │   ├── im_chat.html            #   【团队2】聊天窗口
│   │   ├── im_contacts.html        #   【团队2】通讯录
│   │   ├── admin_im_groups.html    #   【团队2】后台群管理
│   │   ├── admin_im_files.html     #   【团队2】后台文件管理
│   │   ├── admin_im_servers.html   #   【团队2】后台服务器管理
│   │   │
│   │   ├── screen_dashboard.html   #   【团队3】数智大屏
│   │   │
│   │   └── admin_db_config.html    #   【团队5】数据库配置
│   │
│   └── static/
│       ├── css/
│       │   ├── base.css
│       │   ├── chat.css            #   【任务八】问数界面样式
│       │   ├── im.css              #   【团队2】即时通信样式
│       │   └── screen.css          #   【团队3】大屏样式
│       ├── js/
│       │   ├── base.js
│       │   ├── chat.js             #   【任务八】问数交互（SSE/Markdown）
│       │   ├── im.js               #   【团队2】即时通信（WebSocket）
│       │   ├── gesture.js          #   【团队4】手势交互
│       │   └── tts.js              #   【团队4】语音播报
│       └── dist/                   # 第三方库（本地化，禁止 CDN）
│           ├── layui-v2.13.6/
│           ├── bootstrap-5.3.8-dist/
│           ├── fontawesome-free-5.15.4-web/
│           ├── echarts/            # 【团队3】Echarts
│           └── echarts-gl/         # 【团队3】Echarts-GL
│
├── lib/                            # 本地 Python 依赖（不提交 Git）
│   ├── tornado/
│   ├── openai/
│   ├── requests/
│   └── ...
│
└── vendor/                         # 备用库目录（不提交 Git）
```

### 2.2 命名规范总表

| 类别 | 规范 | 示例 |
|------|------|------|
| **Python 文件** | 蛇形（snake_case） | `user.py`, `api_service.py` |
| **HTML 模板** | 蛇形 | `admin_user_manage.html` |
| **CSS/JS 文件** | 蛇形 | `chat.css`, `chat.js` |
| **Python 类** | 大驼峰（PascalCase） | `UserRepository`, `AdminUserListHandler` |
| **Python 方法/函数** | 蛇形 | `get_all_users()`, `_parse_baidu_news()` |
| **私有成员** | 前导下划线 | `_hash_password()` |
| **路由路径** | 小写 + 连字符 | `/admin/user/manage` |
| **数据库表** | 蛇形复数 | `users`, `api_services`, `chat_messages` |
| **数据库字段** | 蛇形 | `create_at`, `password_hash`, `sort_order` |
| **主键** | 统一 `id` | `id INTEGER PRIMARY KEY AUTOINCREMENT` |
| **时间字段** | `create_at` | SQLite `datetime('now')` 默认值 |
| **Git 分支** | `feat/模块名-功能` | `feat/task7-digital-employee` |
| **Git 提交** | 约定式提交 | `feat(task7): add digital employee management` |

---

## 三、数据库表结构（完整）

### 3.1 已有表（已完成任务）

| # | 表名 | 说明 | 所属任务 |
|---|------|------|----------|
| 1 | `users` | 系统用户（含 admin） | 任务一、二 |
| 2 | `modules` | 功能模块/菜单树 | 任务三 |
| 3 | `roles` | 角色定义 | 任务三 |
| 4 | `role_permissions` | 角色-权限关联 | 任务三 |
| 5 | `model_engines` | AI 模型配置 | 任务四 |
| 6 | `watch_sources` | 瞭望数据源 | 任务五 |
| 7 | `watch_data` | 瞭望采集数据仓库 | 任务五 |
| 8 | `api_services` | 接口 URL 管理 | 任务六 |

### 3.2 digital_employees（任务七）

数字员工：基于大模型 + API 服务的综合业务单元。

```sql
CREATE TABLE IF NOT EXISTS digital_employees(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                          -- 数字员工名称（如：川小农）
    alias TEXT NOT NULL UNIQUE,                  -- 别名（如：@川小农）
    category TEXT DEFAULT 'AI',                  -- 分类：AI / 普通
    agent_type TEXT DEFAULT 'chat',              -- 类型：chat（AI对话）/ api（接口调用）
    api_service_id INTEGER DEFAULT 0,            -- 关联 api_services.id（普通类使用）
    prompt TEXT DEFAULT '',                      -- AI 提示词（AI 类使用）
    icon TEXT DEFAULT 'fa-robot',                -- FontAwesome 图标标识
    description TEXT DEFAULT '',                 -- 功能说明
    sort_order INTEGER DEFAULT 0,                -- 排序权重
    status INTEGER NOT NULL DEFAULT 1,           -- 1=启用 0=禁用
    create_at TEXT NOT NULL DEFAULT(datetime('now'))
);
```

**初始数据**（系统启动时自动插入）：

| name | alias | category | agent_type | api_service_id | prompt |
|------|-------|----------|------------|----------------|--------|
| 川小农 | @川小农 | AI | chat | 0 | 你是"川小农"，四川农业大学的智能助手…… |
| 天气 | @天气 | 普通 | api | 天气API的ID | - |
| 音乐 | @音乐 | 普通 | api | 音乐API的ID | - |

### 3.3 chat_sessions（任务八）

对话会话头表。

```sql
CREATE TABLE IF NOT EXISTS chat_sessions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,                    -- 所属用户
    title TEXT DEFAULT '新对话',                  -- 会话标题
    model_id INTEGER DEFAULT 0,                  -- 关联 model_engines.id（选用的模型）
    create_at TEXT NOT NULL DEFAULT(datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### 3.4 chat_messages（任务八）

对话消息明细表。

```sql
CREATE TABLE IF NOT EXISTS chat_messages(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,                 -- 所属会话
    role TEXT NOT NULL,                          -- user / assistant / system
    content TEXT NOT NULL,                       -- 消息内容（支持 Markdown）
    msg_type TEXT DEFAULT 'text',                -- text / employee_call / sql_query
    employee_id INTEGER DEFAULT 0,               -- 关联 digital_employees.id
    create_at TEXT NOT NULL DEFAULT(datetime('now')),
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
);
```

### 3.5 团队任务 2 — 即时通信表（设计参考）

```sql
-- 好友关系
CREATE TABLE IF NOT EXISTS im_friends(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    friend_id INTEGER NOT NULL,
    remark TEXT DEFAULT '',                      -- 备注名
    status INTEGER DEFAULT 1,                    -- 1=好友 0=已解除
    create_at TEXT NOT NULL DEFAULT(datetime('now'))
);

-- 群组
CREATE TABLE IF NOT EXISTS im_groups(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    owner_id INTEGER NOT NULL,                   -- 群主
    announcement TEXT DEFAULT '',
    status INTEGER DEFAULT 1,
    create_at TEXT NOT NULL DEFAULT(datetime('now'))
);

-- 群成员
CREATE TABLE IF NOT EXISTS im_group_members(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT DEFAULT 'member',                  -- owner / admin / member
    create_at TEXT NOT NULL DEFAULT(datetime('now'))
);

-- 聊天消息
CREATE TABLE IF NOT EXISTS im_messages(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    msg_type TEXT DEFAULT 'text',                -- text / image / file / emoji
    content TEXT,
    file_path TEXT DEFAULT '',
    sender_id INTEGER NOT NULL,
    receiver_type TEXT NOT NULL,                  -- user / group
    receiver_id INTEGER NOT NULL,
    create_at TEXT NOT NULL DEFAULT(datetime('now'))
);

-- 文件管理
CREATE TABLE IF NOT EXISTS im_files(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT NOT NULL,
    file_size INTEGER DEFAULT 0,
    file_hash TEXT DEFAULT '',                   -- 用于去重
    uploader_id INTEGER NOT NULL,
    create_at TEXT NOT NULL DEFAULT(datetime('now'))
);

-- 聊天服务器配置
CREATE TABLE IF NOT EXISTS im_servers(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    host TEXT NOT NULL,
    port INTEGER DEFAULT 10087,
    status INTEGER DEFAULT 1,
    current_load INTEGER DEFAULT 0,
    create_at TEXT NOT NULL DEFAULT(datetime('now'))
);
```

### 3.6 团队任务 5 — 数据库配置表

```sql
CREATE TABLE IF NOT EXISTS db_configs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    db_type TEXT NOT NULL,                       -- sqlite / mysql
    host TEXT DEFAULT '',
    port INTEGER DEFAULT 3306,
    database_name TEXT DEFAULT '',
    username TEXT DEFAULT '',
    password TEXT DEFAULT '',
    is_active INTEGER DEFAULT 0,                 -- 1=当前使用的数据库
    create_at TEXT NOT NULL DEFAULT(datetime('now'))
);
```

---

## 四、API 路由规范（完整路由表）

### 4.1 通用规范

| 项目 | 规范 |
|------|------|
| 管理侧前缀 | `/admin/{模块}/{动作}` |
| 用户侧前缀 | `/api/{模块}/{动作}` 或直接路径 |
| 列表接口 | `GET /admin/{模块}/list?page=1&limit=20` |
| 新增 | `POST /admin/{模块}/add` |
| 修改 | `POST /admin/{模块}/update` |
| 删除 | `POST /admin/{模块}/delete` |
| 流式接口 | `GET /admin/{模块}/stream`（SSE 协议） |
| WebSocket | `ws://{host}/ws/{模块}`（团队2） |

### 4.2 管理侧路由（完整）

```
# ── 认证 ──
/admin/login                   GET/POST   管理登录
/admin/logout                  POST       管理登出

# ── 框架 ──
/admin                         GET        管理后台框架（左菜单右 iframe）
/admin/home                    GET        管理首页
/admin/menu                    GET        动态菜单 JSON

# ── 任务二：用户管理 ──
/admin/user/manage             GET        用户管理页面
/admin/user/list               GET        用户列表
/admin/user/add                POST       新增用户
/admin/user/update             POST       修改用户
/admin/user/delete             POST       删除用户

# ── 任务三：模块管理 ──
/admin/module/manage           GET        模块管理页面
/admin/module/list             GET        模块列表
/admin/module/add              POST       新增模块
/admin/module/update           POST       修改模块
/admin/module/delete           POST       删除模块

# ── 任务三：角色管理 ──
/admin/role/manage             GET        角色管理页面
/admin/role/list               GET        角色列表
/admin/role/add                POST       新增角色
/admin/role/update             POST       修改角色
/admin/role/delete             POST       删除角色
/admin/role/select             GET        角色下拉列表

# ── 任务三：权限管理 ──
/admin/permission/manage       GET        权限管理页面
/admin/permission/load         GET        加载权限数据
/admin/permission/save         POST       保存权限配置

# ── 任务四：模型引擎 ──
/admin/model/manage            GET        模型配置页面
/admin/model/list              GET        模型列表
/admin/model/add               POST       新增模型
/admin/model/update            POST       修改模型
/admin/model/delete            POST       删除模型
/admin/model/setdefault        POST       设置默认模型
/admin/model/chat              POST       模型对话测试
/admin/model/chatstream        GET        SSE 流式对话

# ── 任务五：瞭望管理 ──
/admin/watch/source            GET        瞭望源管理页面
/admin/watch/source/list       GET        瞭望源列表
/admin/watch/source/add        POST       新增瞭望源
/admin/watch/source/update     POST       修改瞭望源
/admin/watch/source/delete     POST       删除瞭望源
/admin/watch/collect           GET        采集任务页面
/admin/watch/docollect         POST       执行采集
/admin/watch/data              GET        数据仓库页面
/admin/watch/data/list         GET        数据仓库列表
/admin/watch/data/delete       POST       删除数据

# ── 任务六：接口管理 ──
/admin/api/manage              GET        接口管理页面
/admin/api/list                GET        接口列表
/admin/api/add                 POST       新增接口
/admin/api/update              POST       修改接口
/admin/api/delete              POST       删除接口

# ── 任务七：数字员工管理 ──
/admin/employee/manage         GET        数字员工页面
/admin/employee/list           GET        数字员工列表
/admin/employee/add            POST       新增数字员工
/admin/employee/update         POST       修改数字员工
/admin/employee/delete         POST       删除数字员工

# ── 团队任务 2：后台群管理 ──
/admin/im/groups               GET        群管理页面
/admin/im/groups/list          GET        群列表
/admin/im/groups/dissolve      POST       解散群
/admin/im/groups/ban           POST       封禁/解封群
/admin/im/groups/members       GET        群成员列表
/admin/im/groups/announcement  POST       发布公告

# ── 团队任务 2：后台文件管理 ──
/admin/im/files                GET        文件管理页面
/admin/im/files/list           GET        文件列表
/admin/im/files/delete         POST       删除文件

# ── 团队任务 2：后台服务器管理 ──
/admin/im/servers              GET        服务器管理页面
/admin/im/servers/list         GET        服务器列表
/admin/im/servers/add          POST       新增服务器
/admin/im/servers/update       POST       修改服务器
/admin/im/servers/delete       POST       删除服务器

# ── 团队任务 5：数据库配置 ──
/admin/db/config               GET        数据库配置页面
/admin/db/config/list          GET        配置列表
/admin/db/config/add           POST       新增配置
/admin/db/config/switch        POST       切换当前数据库
```

### 4.3 用户侧路由（完整）

```
# ── 认证 ──
/auth/login                    GET/POST   用户登录
/auth/logout                   POST       用户登出
/auth/register                 GET/POST   用户注册【任务八】

# ── 首页 ──
/                              GET        用户侧首页
/chat                          GET        问数对话界面【任务八】

# ── 任务八：智能问数 ──
/api/chat/send                 POST       发送消息
/api/chat/stream               GET        SSE 流式响应
/api/chat/sessions             GET        会话列表
/api/chat/history              GET        消息历史
/api/chat/session/add          POST       新建会话
/api/chat/session/delete       POST       删除会话
/api/employee/list             GET        数字员工列表
/api/model/list                GET        可用模型列表

# ── 团队任务 2：即时通信 ──
/im                            GET        即时通信首页
/ws/im                         WebSocket  WebSocket 连接
/api/im/friends/search         GET        查找用户
/api/im/friends/add            POST       添加好友
/api/im/friends/list           GET        好友列表
/api/im/groups/create          POST       创建群组
/api/im/groups/list            GET        群组列表
/api/im/groups/join            POST       加入群组
/api/im/files/upload           POST       上传文件
/api/im/files/download         GET        下载文件
```

---

## 五、任务分解与详细需求

---

### 任务一：后台框架 + 管理登录（已完成）

**目标**：搭建管理后台基础框架，实现管理员登录。

**验收标准**：
- [x] 响应式沉浸式登录页，账号 admin / admin888
- [x] Layui 经典左侧菜单 + 右侧 iframe 布局
- [x] 动态菜单（从数据库 modules 表加载）
- [x] XSRF 安全防护

**关键文件**：
- `app/templates/admin_login.html`
- `app/templates/admin_index.html`
- `app/controllers/admin.py → AdminLoginHandler / AdminIndexHandler`

---

### 任务二：用户管理（已完成）

**目标**：实现后台用户增删改查及批量删除。

**验收标准**：
- [x] 用户列表分页（20 条/页）
- [x] 新增 / 编辑 / 删除 / 批量删除
- [x] 超级管理员 admin 不可删除保护
- [x] 用户名唯一性校验

---

### 任务三：模块·权限·角色管理（已完成）

**目标**：实现模块树管理、角色定义及权限二级联动。

**验收标准**：
- [x] 功能模块树形管理（新增/编辑/删除）
- [x] 角色 CRUD（系统内置角色保护）
- [x] 角色-权限二级联动选择
- [x] 超级管理员自动拥有全部权限

---

### 任务四：模型引擎（已完成）

**目标**：实现 AI 模型配置的橱窗式管理。

**验收标准**：
- [x] 科幻风格模型卡片展示
- [x] 新增 / 编辑 / 删除模型配置（支持 OpenAI 范式）
- [x] 设置默认模型
- [x] SSE 流式对话测试（打字机效果）
- [x] Token 消耗统计

---

### 任务五：瞭望管理（已完成）

**目标**：实现数据采集及数据仓库管理。

**验收标准**：
- [x] 数据源动态规则配置（URL + Headers + 占位符）
- [x] 暗色系搜索引擎风格采集界面
- [x] 百度新闻三位一体解析引擎（JSON → DOM → Regex）
- [x] 分页数据仓库（20 条/页）+ 批量删除
- [x] `requests.Session` + `verify=False` + 禁用 br/zstd

---

### 任务六：接口管理（已完成）

**目标**：实现互联网 API 接口的集中管理模块。

**验收标准**：
- [x] 接口 CRUD + 分页列表（20 条/页）
- [x] 支持字段：名称、URL、请求方式、返回格式、QPS 限制、Token
- [x] 状态开关（启用 / 禁用）
- [x] 系统启动时自动插入示例数据（随机音乐、三日天气）

---

### 任务七：数字员工管理

**目标**：实现后台数字员工的可视化管理，用户侧通过 `@别名` 调用。

**需求说明**：
> 数字员工是基于大模型服务 + 接口管理中的 API 服务完成的综合业务管理功能。用户侧可通过 `@别名` 唤起对应服务。

#### 7.1 数字员工分类

| 分类 | 类型 | 工作原理 | 示例 |
|------|------|---------|------|
| **AI 类** | `chat` | 调用默认模型 + 自定义 Prompt 进行智能对话 | `@川小农: 介绍一下川农大` |
| **普通类** | `api` | 调用关联的 API 接口服务，获取数据返回 | `@天气 北京市` → 调用天气 API |
| **普通类** | `api` | 调用关联的 API 接口服务，获取数据返回 | `@音乐` → 调用随机音乐 API |

#### 7.2 后台管理界面

**UI 要求**（与管理后台一致）：
- 采用 Layui 表格风格，与瞭望源管理、接口管理页面保持视觉一致
- 列表列：ID / 名称 / 别名 / 分类 / 类型 / 关联API / 状态 / 创建时间 / 操作
- 表单包含完整字段（见 `digital_employees` 表结构）

**表单字段**：
| 字段 | 类型 | 说明 |
|------|------|------|
| 名称 | 文本 | 如"川小农" |
| 别名 | 文本 | 如"@川小农"（唯一） |
| 分类 | 下拉 | AI / 普通 |
| 类型 | 下拉 | chat / api |
| 关联API | 下拉 | 从 `api_services` 加载（普通类必选） |
| Prompt | 文本域 | AI 提示词（AI 类必填） |
| 图标 | 文本 | FontAwesome 图标类名 |
| 描述 | 文本域 | 功能说明 |
| 排序 | 数字 | 排序权重 |
| 状态 | 开关 | 启用 / 禁用 |

#### 7.3 前端调用逻辑（任务八实现）

```
用户输入 "@天气 北京市"
  → 前端解析出 alias="@天气", param="北京市"
  → 后端查询 digital_employees WHERE alias="@天气"
  → 判断为 category="普通", agent_type="api"
  → 根据 api_service_id 取出对应的 URL 和参数模板
  → 调用外部 API → 返回 JSON → 渲染为消息卡片
```

#### 7.4 验收标准

- [ ] 数字员工管理界面可正常 CRUD
- [ ] 启动时自动插入川小农（AI类）、天气（普通类）、音乐（普通类）
- [ ] AI 类可配置 Prompt 提示词
- [ ] 普通类可选择关联 API
- [ ] 别名唯一性校验
- [ ] 菜单自动注入系统导航

#### 7.5 关键文件清单

| 文件 | 说明 |
|------|------|
| `app/models/db.py` | `digital_employees` 建表 + 初始数据 |
| `app/models/digital_employee.py` | DigitalEmployeeRepository（CRUD） |
| `app/controllers/admin.py` | 5 个 Handler（Manage/List/Add/Update/Delete） |
| `app/templates/admin_employee_manage.html` | 前端管理界面 |
| `app.py` | 注册 5 条路由 + import |

---

### 任务八：前端用户侧（登录·注册·问数）

**目标**：实现用户前端登录、注册、智能问数对话界面。

#### 8.1 用户登录

**需求**：
- 利用后端已有认证模块，与管理用户共用一套鉴权逻辑
- 区分角色：`user`（普通用户）、`admin`（管理员，不可从前端登录）
- 普通用户登录后跳转至用户侧主页 `/chat`
- 预留会员角色（`vip`），本期不开发

**路由**：`/auth/login` GET/POST（已有，需确认模板适配角色）

#### 8.2 用户注册

**需求**：
- 允许用户自主注册为普通用户
- 注册字段：用户名、密码、确认密码
- 注册后自动登录并跳转至 `/chat`
- 用户名唯一性校验
- 密码强度提示（≥6 位）

**路由**：`/auth/register` GET/POST

**前端模板**：`register.html`

**后端处理**：
```python
class RegisterHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("register.html", error=None)
    def post(self):
        # 校验 → UserRepository.create_user(username, password, role="user")
        # → 设置 cookie → 跳转 /chat
```

#### 8.3 智能问数界面

**核心定位**：类似 ChatGPT / 豆包的对话风格。

**布局设计**：

```
┌──────────────────────────────────────────────────┐
│  左侧面板（300px）           │  右侧工作区（剩余）  │
│                              │                    │
│  ┌──── 模型切换 ────┐       │  ┌── 消息列表 ──┐   │
│  │ [GPT-3.5 ▼]      │       │  │              │   │
│  └──────────────────┘       │  │ 你好！        │   │
│                              │  │ ───────────  │   │
│  ┌── 历史对话 ────┐         │  │ 你有什么问题？│   │
│  │ ✓ 今天天气如何  │         │  │              │   │
│  │ ○ 川农大介绍    │         │  └──────────────┘   │
│  │ ○ 随机来首歌    │         │                    │
│  │ 新建对话 [+]    │         │  ┌── 输入区 ───┐   │
│  └────────────────┘         │  │ @天气 北京  📤│   │
│                              │  └──────────────┘   │
└──────────────────────────────────────────────────┘
```

**左侧面板功能**：
| 区域 | 功能 | 说明 |
|------|------|------|
| 模型切换 | 下拉框 | 从 `model_engines` 加载，切换后后续对话使用该模型 |
| 历史会话 | 列表 | 从 `chat_sessions` 加载，点击回放，支持新建/删除 |
| 当前会话 | 高亮 | 当前正在对话的会话标记为选中状态 |

**右侧工作区功能**：
| 区域 | 功能 | 说明 |
|------|------|------|
| 消息列表 | 流式渲染 | SSE 接收数据，Markdown 渲染，打字机效果 |
| 输入框 | 普通输入 + @唤起 | 输入 `@` 弹出数字员工列表，支持 `@别名 参数` |
| 发送按钮 | 发送消息 | 调用 `/api/chat/send` |

#### 8.4 核心业务逻辑

**业务流 1：普通对话**
```
用户输入 "你好" 
  → POST /api/chat/send
  → 后端识别无 @ 前缀，无 SQL 意图
  → 调用 model_engines 中默认模型的 API（SSE 流式）
  → 返回 Markdown 渲染的消息
```

**业务流 2：智能问数（SQL 查询）**
```
用户输入 "最新一条采集数据是什么？"
  → POST /api/chat/send
  → 后端意图识别 + LLM 判断 → 发现需要查数据库
  → LLM 生成 SQL：SELECT * FROM watch_data ORDER BY id DESC LIMIT 1
  → 执行 SQL → 获取结果 → LLM 生成自然语言回答
  → SSE 流式返回
```

**业务流 3：@数字员工**
```
用户输入 "@天气 北京市"
  → 前端 / 后端解析 @别名
  → 查询 digital_employees WHERE alias="@天气"
  → category="普通" → 调用关联的天气 API (city=北京市)
  → 返回 JSON → 渲染为天气卡片
```

**业务流 4：@AI 数字员工**
```
用户输入 "@川小农: 介绍一下川农大"
  → 解析 @川小农
  → category="AI" → 取 prompt + 用户问题
  → 调用默认模型（带 system prompt）= SSE 流式返回
```

#### 8.5 验收标准

- [ ] 注册页面可正常注册新用户
- [ ] 登录后进入对话界面 `/chat`
- [ ] 左侧显示历史会话列表，可新建/删除
- [ ] 左侧支持模型切换下拉框
- [ ] 右侧消息列表流式渲染 Markdown
- [ ] 输入框支持 `@` 唤起数字员工
- [ ] 支持普通对话、@数字员工、SQL 问数三种模式
- [ ] 对话历史可点击回放

#### 8.6 关键文件清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `app/templates/login.html` | 视图 | 用户登录页面 |
| `app/templates/register.html` | 视图 | 用户注册页面 |
| `app/templates/chat.html` | 视图 | 问数对话界面（核心） |
| `app/static/css/chat.css` | 样式 | 对话界面样式 |
| `app/static/js/chat.js` | 脚本 | SSE、Markdown 渲染、@唤起逻辑 |
| `app/controllers/auth.py` | 控制器 | 注册 Handler |
| `app/controllers/chat.py` | 控制器 | 问数 Handler（send/stream/sessions） |
| `app/models/chat_session.py` | 模型 | 会话 CRUD |
| `app/models/chat_message.py` | 模型 | 消息 CRUD |
| `app.py` | 入口 | 路由注册 |

---

### 团队任务 1：功能完整性（20 分）

**目标**：完整实现用户侧 + 管理侧全部功能，达到产品级交付标准。

**考察重点**：
- 需求完整性：覆盖所有已规划功能
- 功能完整性：每个功能可正常使用
- 系统风格去 AI 化：界面风格统一，不显生硬
- 软件成熟度：异常处理完善，无崩溃
- 系统安全能力：XSRF、SQL注入防护、会话安全
- 产品化成熟度：错误提示友好、操作流畅

---

### 团队任务 2：仿微信即时通信子系统（30 分）

#### 2.1 基础架构

- 参考微信聊天模式，在用户侧复刻 1:1 聊天应用
- 用户注册后进入主界面，可选择进入智能问数或智能聊天子系统
- 基于 Tornado WebSocket 实现实时消息推送

#### 2.2 智能聊天核心功能

| 功能 | 说明 |
|------|------|
| 1v1 私聊 | 点对点实时消息 |
| 群聊 | 多人群组实时消息 |
| 通讯录管理 | 好友列表、群组列表 |
| 用户在线查找 | 通过用户名搜索 |
| 数字员工集成 | 拉入群聊，@触发自动回复 |

#### 2.3 好友与群组管理

- 支持通过用户名在线查找并添加好友
- 支持拉取好友创建群组

#### 2.4 消息交互能力

| 消息类型 | 说明 |
|---------|------|
| 文本消息 | 纯文本即时收发 |
| emoji / 动态表情 | 支持表情选择器 |
| 文件收发 | 上传/下载文件，后台集中管理 |

#### 2.5 数字员工集成（聊天场景）

| 员工 | 说明 |
|------|------|
| 川农小助手 | 限定川农场景，重点实现提示词工程与多轮对话 |
| 天气小助手 | 输入城市名，返回天气卡片 + 动态天气特效 |
| 毒鸡汤助手 | 随机回复毒鸡汤语句 |
| 系统原有 AI 员工 | 同步支持群聊 @调用 |

#### 2.6 后台管理侧新增

| 模块 | 功能 |
|------|------|
| 群管理 | 解散/封禁/管控群聊、查看成员、发布公告 |
| 文件管理 | 集中管理文件，去重存储 |
| 服务器管理 | 多聊天服务器配置，自动切换 |
| 工具与员工管理 | AI 调用工具集可视化，为数字员工绑定专属工具 |

#### 2.7 关键文件清单

| 文件 | 说明 |
|------|------|
| `app/controllers/im.py` | WebSocket + HTTP Handler |
| `app/models/im_friend.py` | 好友关系 |
| `app/models/im_group.py` | 群组 |
| `app/models/im_message.py` | 聊天消息 |
| `app/models/im_file.py` | 文件管理 |
| `app/templates/im_index.html` | 即时通信首页 |
| `app/templates/im_chat.html` | 聊天窗口 |
| `app/templates/im_contacts.html` | 通讯录 |
| `app/static/js/im.js` | WebSocket 客户端 |
| `app/static/css/im.css` | 样式 |

---

### 团队任务 3：智慧舆情（20 分）

#### 3.1 数智大屏

| 模块 | 技术 | 说明 |
|------|------|------|
| 3D 地球 | Echarts-GL | 数据可视化 3D 展示 |
| 词云 | Wordcloud | 关键词聚类可视化 |
| 数据统计 | Echarts | 柱状图、折线图、饼图 |
| 大屏布局 | 自定义 CSS | 全屏、自适应 |

#### 3.2 智能舆情分析

- 通过 AI 模型自主分析智能聊天子系统、瞭望子系统中的数据
- 实现舆情风险识别、预警
- 分析结果在大屏中展示

#### 3.3 关键文件清单

| 文件 | 说明 |
|------|------|
| `app/templates/screen_dashboard.html` | 数智大屏 |
| `app/static/js/screen.js` | 大屏交互逻辑 |
| `app/static/css/screen.css` | 大屏样式 |
| `app/controllers/screen.py` | 大屏数据 API |

---

### 团队任务 4：视觉/语音功能增强（20 分）

#### 4.1 手势交互

- 基于视觉实现手势快捷操作系统
- 设计并实现 **不少于 5 种** 手势交互效果
- 手势示例：滑动翻页、捏合缩放、双击点赞、画圈搜索、挥手返回

#### 4.2 语音播报

- 在合适的业务场景中实现语音播报
- 场景示例：新消息提醒、采集完成通知、天气播报
- 避免功能生硬堆砌

#### 4.3 自动化功能

- 定时自动爬取（基于 APScheduler 或 Tornado 的周期性回调）
- 自动工作流（如：每天早 8 点采集新闻 → 分析 → 推送）
- 具体需求由小组内分析设计完成

#### 4.4 关键文件清单

| 文件 | 说明 |
|------|------|
| `app/static/js/gesture.js` | 手势识别逻辑 |
| `app/static/js/tts.js` | 语音播报（Web Speech API） |
| `app/controllers/automation.py` | 自动化调度 Handler |
| `app/models/auto_task.py` | 自动化任务模型 |

---

### 团队任务 5：多数据库支持（10 分）

#### 5.1 需求

- 系统需同时支持 **MySQL** 与 **SQLite** 数据库
- 后台支持数据库切换，默认使用 SQLite

#### 5.2 设计思路

- 抽象数据库连接层，通过配置决定使用哪种数据库
- 启动时从 `db_configs` 表读取 `is_active=1` 的配置
- 切换数据库时，重建连接池/连接对象

#### 5.3 关键文件

| 文件 | 说明 |
|------|------|
| `app/models/db.py` | 重构：根据配置选择 SQLite/MySQL 连接 |
| `app/models/db_config.py` | 数据库配置 CRUD |
| `app/templates/admin_db_config.html` | 数据库配置管理页面 |

---

## 六、开发规范（团队强制执行）

### 6.1 代码规范

```python
# ===== 正确示例 =====

# 类：大驼峰命名
class UserRepository:
    # 方法：蛇形命名
    @staticmethod
    def get_all_users(page=1, page_size=20):
        # 参数化查询（禁止字符串拼接）
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM users LIMIT ? OFFSET ?",
                (page_size, (page - 1) * page_size)
            )
            return [dict(row) for row in rows]

# Handler：大驼峰 + 继承 AdminBaseHandler
class AdminApiListHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1))
        limit = int(self.get_argument("limit", 20))
        data, total = ApiServiceRepository.get_list(page, limit)
        # 统一返回格式
        self.write({"code": 0, "msg": "", "count": total, "data": data})
```

### 6.2 前端规范（静态资源路径）

```html
<!-- Layui（管理侧） -->
<link rel="stylesheet" href="{{ static_url('dist/layui-v2.13.6/layui/css/layui.css') }}">
<script src="/static/dist/layui-v2.13.6/layui/layui.js"></script>

<!-- FontAwesome（通用） -->
<link rel="stylesheet" href="{{ static_url('dist/fontawesome-free-5.15.4-web/css/all.min.css') }}">

<!-- Bootstrap（用户侧） -->
<link rel="stylesheet" href="{{ static_url('dist/bootstrap-5.3.8-dist/css/bootstrap.min.css') }}">

<!-- Echarts（团队3大屏） -->
<script src="/static/dist/echarts/echarts.min.js"></script>
```

### 6.3 AJAX 规范（管理侧）

```javascript
// XSRF 令牌（所有 POST 必须携带）
function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (settings.type === 'POST') {
            xhr.setRequestHeader("X-XSRFToken", getCookie("_xsrf"));
        }
    }
});
```

### 6.4 控制器-模型-视图 数据流

```
用户请求 → URL路由匹配
         → Handler.get()/post()
         → Repository.方法() → SQLite/MySQL
         → 返回数据
         → self.render("模板.html") 或 self.write(JSON)
```

### 6.5 新模块接入规范（必须执行）

所有新增模块必须执行以下 **3 步注册**：

| 步骤 | 位置 | 操作 |
|------|------|------|
| ① 数据库 | `app/models/db.py` 的 `init_db()` | `CREATE TABLE IF NOT EXISTS` + 插入菜单数据 + 插入初始数据 |
| ② 路由 | `app.py` | `import Handler` + `(r"/path", Handler)` |
| ③ 权限 | `app/models/db.py` 的 `init_db()` | 自动为超级管理员插入 `role_permissions` |

### 6.6 数据处理规范（爬虫）

```python
# Session 维持 Cookie
session = requests.Session()
safe_headers["accept-encoding"] = "gzip, deflate"  # 禁用 br/zstd
session.headers.update(safe_headers)

# 禁用 SSL 验证
resp = session.get(url, timeout=15, verify=False)

# 三位一体解析
# 方案1：JSON 提取 → 方案2：DOM 解析 → 方案3：正则兜底
```

### 6.7 响应格式规范

```json
// 列表接口
{"code": 0, "msg": "", "count": 100, "data": [...]}

// 操作接口（成功）
{"code": 0, "msg": "操作成功"}

// 操作接口（失败）
{"code": 1, "msg": "错误描述"}
```

---

## 七、提交规范（Commit Convention）

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat:` | 新功能 | `feat(task7): add digital employee CRUD management` |
| `fix:` | 修复 | `fix(watch): fix brotli decompression encoding error` |
| `refactor:` | 重构 | `refactor: extract db connection as abstract layer` |
| `chore:` | 杂项 | `chore: update requirements.txt` |
| `docs:` | 文档 | `docs: update team development requirements to v3.0` |
| `style:` | 样式 | `style(chat): adjust message bubble spacing` |
| `perf:` | 性能 | `perf(db): add index on watch_data.url` |
| `test:` | 测试 | `test(user): add user registration test cases` |

**提交信息格式**：
```
<type>(<scope>): <description>

# 示例
feat(task7): add digital employee CRUD management
  - DigitalEmployeeRepository with get_list/add/update/delete
  - 5 Handler classes in admin.py
  - admin_employee_manage.html with Layui table
  - Auto-insert seed data for 川小农/天气/音乐
```

---

## 八、分支策略

```
main                     # 稳定版本（仅合并经过 Review 的代码）
  │
  ├── dev                # 开发分支（日常 CI 集成）
  │   │
  │   ├── feat/task7-digital-employee      # 任务七
  │   ├── feat/task8-user-chat             # 任务八
  │   ├── feat/team2-im                    # 团队任务2
  │   ├── feat/team3-screen                # 团队任务3
  │   ├── feat/team4-gesture               # 团队任务4
  │   └── feat/team5-multi-db              # 团队任务5
  │
  └── hotfix/*            # 紧急修复分支
```

**协作流程**：
1. 从 `dev` 创建 `feat/xxx` 分支开发
2. 开发完成后发起 Pull Request → `dev`
3. 代码 Review 通过后合并
4. 阶段性发布时从 `dev` 合并到 `main`

---

## 九、需求状态看板

| 任务ID | 模块 | 优先级 | 分值 | 状态 | 说明 |
|--------|------|--------|------|------|------|
| 任务一 | 后台框架+登录 | P0 | - | ✅ 已完成 | |
| 任务二 | 用户管理 | P0 | - | ✅ 已完成 | |
| 任务三 | 模块·权限·角色 | P0 | - | ✅ 已完成 | |
| 任务四 | 模型引擎 | P0 | - | ✅ 已完成 | |
| 任务五 | 瞭望管理 | P0 | - | ✅ 已完成 | |
| 任务六 | 接口管理 | P0 | - | ✅ 已完成 | 含示例数据 |
| **任务七** | **数字员工管理** | **P0** | **-** | **⬜ 待开发** | **本次核心** |
| **任务八** | **前端用户侧** | **P0** | **-** | **⬜ 待开发** | **登录·注册·问数** |
| **团队1** | **功能完整性** | **P0** | **20** | **⬜ 待开发** | **交付要求** |
| **团队2** | **仿微信通信** | **P1** | **30** | **⬜ 待开发** | **最高分值** |
| **团队3** | **智慧舆情** | **P1** | **20** | **⬜ 待开发** | Echarts + 3D |
| **团队4** | **视觉/语音增强** | **P2** | **20** | **⬜ 待开发** | 手势+语音+自动化 |
| **团队5** | **多数据库支持** | **P2** | **10** | **⬜ 待开发** | SQLite+MySQL |

---

> **文档维护者**：AI 智能瞭望与智能问数系统 开发团队
> **更新记录**：v3.0 — 2026-05-24 — 重构全量文档，新增任务七/八/团队1~5详细需求、完整目录结构、命名规范、路由总表、数据库全表
