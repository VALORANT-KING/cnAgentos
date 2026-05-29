# AI 智能瞭望与智能问数系统

基于 **Tornado MVC** 架构的企业级 B/S Web 应用，集成 **AI 大模型对话**、**智能数据采集（瞭望）**、**API 接口集中管理**、**数字员工调度**、**仿微信即时通信** 及 **智慧舆情分析** 等功能。

---

## 技术栈

| 层级 | 技术选型 |
|------|----------|
| 后端框架 | Tornado 6.5.5 |
| 数据库 | SQLite3（`env/database/app.db`） |
| AI SDK | OpenAI Python SDK（兼容任意 OpenAI 范式 API） |
| 任务调度 | APScheduler |
| 爬虫引擎 | Requests + BeautifulSoup4 |
| 管理侧 UI | Layui 2.13.6 |
| 用户侧 UI | Bootstrap 5.3 + FontAwesome 5.15 |
| 可视化 | Echarts + Echarts-GL |
| 实时通信 | WebSocket（Tornado 原生） |
| Python | 3.12+ |

---

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 首次运行（自动创建数据库和初始数据）
python app.py

# 访问
# 管理后台：http://127.0.0.1:10086/admin/login   (admin / admin888)
# 用户首页：http://127.0.0.1:10086/home
# 智能聊天：http://127.0.0.1:10086/im
```

---

## 功能模块

### 管理后台（`/admin/*`）

| 模块 | 路径 | 说明 |
|------|------|------|
| 用户管理 | `/admin/user/manage` | 用户增删改查、批量删除、分页 |
| 模块管理 | `/admin/module/manage` | 功能模块树形管理 |
| 角色管理 | `/admin/role/manage` | 角色定义 + 权限二级联动 |
| 权限管理 | `/admin/permission/manage` | 角色-模块权限配置 |
| 模型引擎 | `/admin/model/manage` | AI 模型配置、SSE 流式对话测试 |
| 瞭望源管理 | `/admin/watch/source` | 数据采集源动态规则配置 |
| 瞭望采集 | `/admin/watch/collect` | 关键词 + 多源并发采集 |
| 数据仓库 | `/admin/watch/data` | 采集数据分页查看、批量删除 |
| 接口管理 | `/admin/api/manage` | 互联网 API 集中管理 |
| 数字员工 | `/admin/employee/manage` | AI/普通员工可视化 CRUD |
| 员工工具 | `/admin/employee/tools` | 工具集管理 + 员工绑定 |
| 自动化采集 | `/admin/auto/manage` | 定时采集任务调度（APScheduler） |
| 群管理 | `/admin/im/groups` | 群解散/封禁/公告 |
| 文件管理 | `/admin/im/files` | 聊天文件集中管理 |
| 服务器管理 | `/admin/im/servers` | 多聊天服务器配置 |
| 数据库配置 | `/admin/db/config` | SQLite/MySQL 多库切换 |

### 用户侧

| 模块 | 路径 | 说明 |
|------|------|------|
| 首页 | `/home` | 子系统选择入口 |
| 智能问数 | `/chat` | AI 对话、SQL 问数、@数字员工 |
| 智能聊天 | `/im` | 仿微信即时通信 |
| 数智大屏 | `/screen/dashboard` | 3D 地球、词云、舆情分析 |

### 智能聊天功能

- 好友/群组通讯录、在线用户搜索
- 1v1 私聊 + 群聊，WebSocket 实时推送
- 文本 / Emoji / 动态表情 / 文件收发
- 群聊 @数字员工（天气卡片、音乐卡片、毒鸡汤卡片、AI 对话）
- 新消息语音播报（TTS）
- 多服务器自动切换 + 断线重连

### 数字员工

| 员工 | 别名 | 类型 | 功能 |
|------|------|------|------|
| 川小农 | `@川小农` | AI | 川农大智能助手（多轮对话） |
| 天气 | `@天气` | API | 三日天气预报卡片 |
| 音乐 | `@音乐` | API | 随机网易云音乐推荐卡片 |
| 毒鸡汤 | `@毒鸡汤` | 本地 | 随机毒鸡汤语录卡片 |

---

## 项目结构

```
cnAgentos/
├── app.py                    # 主入口 + 全量路由注册
├── requirements.txt          # Python 依赖
├── README.md                 # 本文件
├── requirements.md           # 团队开发需求文档
├── .gitignore
│
├── env/
│   ├── database/
│   │   └── app.db            # SQLite 数据库文件
│   ├── Lib/site-packages/    # Python 依赖（本地化）
│   └── uploads/im/           # 聊天文件存储
│
├── app/
│   ├── scheduler.py          # 自动化任务调度器
│   ├── controllers/
│   │   ├── base.py           # BaseHandler 基类
│   │   ├── auth.py           # 用户认证
│   │   ├── home.py           # 用户首页
│   │   ├── chat.py           # 智能问数
│   │   ├── im.py             # 即时通信（WebSocket + HTTP）
│   │   ├── admin.py          # 管理侧所有 Handler
│   │   └── screen.py         # 数智大屏数据 API
│   ├── models/
│   │   ├── db.py             # 数据库连接 + 建表 + 初始数据
│   │   ├── user.py           # 用户 CRUD
│   │   ├── module.py         # 功能模块 CRUD
│   │   ├── role.py           # 角色 CRUD
│   │   ├── model_engine.py   # 模型引擎 CRUD
│   │   ├── watch.py          # 瞭望源 + 数据仓库 CRUD
│   │   ├── api_service.py    # 接口管理 CRUD
│   │   ├── digital_employee.py   # 数字员工 CRUD
│   │   ├── employee_tool.py  # 员工工具 CRUD
│   │   ├── auto_task.py      # 自动化任务 CRUD
│   │   ├── chat_session.py   # 对话会话 CRUD
│   │   ├── chat_message.py   # 对话消息 CRUD
│   │   ├── db_config.py      # 多数据库配置 CRUD
│   │   ├── db_sync.py        # 数据库同步
│   │   ├── im_friend.py      # 好友关系 CRUD
│   │   ├── im_group.py       # 群组 CRUD
│   │   ├── im_message.py     # 聊天消息 CRUD
│   │   └── im_file.py        # 文件管理 CRUD
│   ├── templates/            # Tornado 模板
│   └── static/
│       ├── css/
│       ├── js/
│       └── dist/             # 第三方库（本地化，禁止 CDN）
```

---

## 开发规范

- **架构模式**：Tornado MVC，管理侧左菜单 + 右 iframe
- **数据库安全**：统一参数化查询，禁止字符串拼接 SQL
- **XSRF 防护**：所有 POST 请求携带 `_xsrf` 令牌
- **爬虫规范**：`requests.Session` + `verify=False`，禁用 br/zstd 编码
- **解析策略**：JSON 提取 → DOM 解析 → 正则兜底（三层保险）
- **禁止 CDN**：所有静态资源本地化存放于 `app/static/dist/`

---

## 辅助脚本

| 文件 | 说明 |
|------|------|
| `init_admin.py` | 重置管理员密码为 admin/admin888 |
| `init_sources.py` | 初始化额外采集源（知乎、微博、头条等） |
| `setup_mysql.py` | MySQL 数据库初始化脚本 |
