# AI 智能瞭望与智能问数系统

## 项目概述

本项目是一个基于 **Tornado** 框架构建的 **B/S 架构** Web 应用系统，采用经典的 **MVC（Model-View-Controller）三层架构**设计。项目定位为 **AI 智能瞭望与智能问数系统**，当前已完成基础框架搭建和用户登录认证功能，后续将逐步扩展 AI 智能分析与数据查询能力。

---

## 技术栈

### 后端技术

| 类别 | 技术 | 版本/说明 |
|------|------|-----------|
| 编程语言 | Python | 3.12.10 |
| Web 框架 | Tornado | 6.5.5 |
| 数据库 | SQLite3 | 内置，轻量级嵌入式数据库 |

### 前端技术

| 类别 | 技术 | 版本/说明 |
|------|------|-----------|
| 前端模板 | HTML5 + Tornado Template | 服务端渲染 |
| UI 框架 | Layui | 2.13.6（本地化部署） |
| CSS 框架 | Bootstrap | 5.3.8（本地化部署） |
| 图标库 | FontAwesome | 5.15.4（本地化部署） |
| 样式 | CSS3 | 基础样式重置与自定义 |
| 脚本 | JavaScript | 前端交互逻辑 |

### 其他

| 类别 | 技术 | 版本/说明 |
|------|------|-----------|
| 虚拟环境 | venv | Python 3.12 标准虚拟环境 |

### 前端组件本地化路径

所有前端组件均已本地化部署，存放于 `app/static/dist/` 目录：

- **Layui**：`app/static/dist/layui-v2.13.6/layui/`
  - CSS：`layui.css`
  - JS：`layui.js`
  - 字体图标：`font/` 目录

- **Bootstrap**：`app/static/dist/bootstrap-5.3.8-dist/`
  - CSS：`css/bootstrap.min.css`
  - JS：`js/bootstrap.bundle.min.js`

- **FontAwesome**：`app/static/dist/fontawesome-free-5.15.4-web/`
  - CSS：`css/all.min.css`
  - Web Fonts：`webfonts/` 目录

> 注意：后续开发中所有静态资源引用必须使用本地路径，禁止引用互联网 CDN 资源。

---

## 目录结构

```
cnAgentos/
├── app.md                          # 项目目录结构说明文档
├── app.py                          # 程序主入口（Tornado 服务器容器）
├── README.md                       # 项目说明文档（本文件）
├── text.py                         # 临时测试脚本（用于创建初始管理员账号）
├── venv/                           # Python 虚拟环境目录
│   └── ...
├── database/                       # SQLite 数据库目录
│   └── app.db                      # SQLite 数据库文件（自动创建）
└── app/                            # 主业务包（MVC 三层架构）
    ├── __init__.py                 # Python 包标识文件
    ├── controllers/                # 控制层（Controller）
    │   ├── __init__.py             # 模块初始化文件
    │   ├── base.py                 # 控制器公共基类（BaseHandler）
    │   ├── auth.py                 # 认证相关控制器（登录/登出）
    │   └── home.py                 # 首页控制器
    ├── models/                     # 模型层（Model）
    │   ├── __init__.py             # 模块初始化文件
    │   ├── db.py                   # 数据库访问层（连接/初始化）
    │   └── user.py                 # 用户数据模型（增删改查/验证）
    ├── static/                     # 静态资源目录
    │   ├── css/
    │   │   └── base.css            # 基础公共样式
    │   └── js/
    │       └── base.js             # 基础公共脚本（空）
    └── templates/                  # 视图层模板目录
        ├── base.html               # 基础公共模板（页面骨架）
        ├── login.html              # 登录页模板
        ├── index.html              # 后台首页模板
        └── register.html           # 注册页模板（空，待开发）
```

---

## 架构说明

### MVC 三层架构

本系统严格遵循 MVC 设计模式，各层职责清晰：

#### 1. Model 层（模型层） - `app/models/`

负责数据访问、业务逻辑和数据库操作。

- **`db.py`** - 数据库访问基础设施
  - `_project_root()` - 获取项目根路径
  - `DB_PATH` - 数据库文件绝对路径
  - `get_connection()` - 获取 SQLite 连接（支持行工厂字典返回）
  - `init_db()` - 初始化数据库表结构

- **`user.py`** - 用户领域模型
  - `_hash_password(password, salt)` - PBKDF2-HMAC-SHA256 密码加密
  - `UserRepository.create_user()` - 创建新用户
  - `UserRepository.get_user_by_username()` - 根据用户名查询用户
  - `UserRepository.verify_user()` - 验证用户名和密码

#### 2. View 层（视图层） - `app/templates/` + `app/static/`

负责用户界面展示和前端交互。

- **模板继承体系**：`base.html`（父模板） → `login.html` / `index.html`（子模板）
- **模板语法**：Tornado Template（`{% extends %}`、`{% block %}`、`{% if %}`、`{% module %}`）
- **静态资源**：通过 `static_url()` 函数引用，支持缓存版本管理

#### 3. Controller 层（控制器层） - `app/controllers/`

负责接收 HTTP 请求、调用 Model 层、渲染 View 层或跳转。

- **`base.py`** - 公共基类
  - `BaseHandler.get_current_user()` - 统一登录态认证机制

- **`auth.py`** - 认证控制器
  - `LoginHandler` - 登录逻辑（GET 渲染页面，POST 验证并写 Cookie）
  - `LogoutHandler` - 登出逻辑（清除 Cookie 并跳转）

- **`home.py`** - 首页控制器
  - `IndexHandler` - 后台首页（需登录访问）

---

## 已实现功能

### 1. 用户登录认证

- **登录页面**：`/auth/login`
  - 支持 GET/POST 请求
  - 表单包含用户名和密码输入框
  - 内置 XSRF 防护
  - 空值校验和错误提示

- **密码验证流程**：
  ```
  用户提交表单 → LoginHandler.post() → UserRepository.verify_user() 
  → get_user_by_username() → PBKDF2 密码比对 → 写入 secure cookie → 跳转首页
  ```

- **安全 Cookie 机制**：
  - 使用 `set_secure_cookie("username", username)` 保存登录状态
  - Cookie 签名密钥：`demo-cookie-secret-change-me`（生产环境需更换）

### 2. 登录态验证

- **BaseHandler 统一认证**：
  - 所有需要登录的 Handler 继承 `BaseHandler`
  - 重写 `get_current_user()` 方法，从 secure cookie 读取用户名
  - 配合 `@tornado.web.authenticated` 装饰器实现自动跳转登录页

### 3. 用户登出

- **登出接口**：`/auth/logout`
  - POST 请求清除 cookie
  - 跳转到登录页

### 4. 数据库初始化

- **自动建表**：服务启动时调用 `init_db()` 检查并创建 `users` 表
- **表结构**：
  ```sql
  CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      salt TEXT NOT NULL,
      create_at TEXT NOT NULL DEFAULT(datetime('now'))
  );
  ```

### 5. 初始管理员账号创建

- **临时脚本**：`text.py`
  - 调用 `UserRepository.create_user("admin", "123456")` 创建测试账号
  - 密码使用 PBKDF2-HMAC-SHA256 加密存储（100,000 次迭代 + 16 字节随机盐）

---

## 路由配置

| 路由 | 处理方法 | 说明 | 认证要求 |
|------|---------|------|---------|
| `/` | `IndexHandler.get()` | 后台首页 | 已登录 |
| `/auth/login` | `LoginHandler.get()` / `LoginHandler.post()` | 登录页/登录提交 | 无 |
| `/auth/logout` | `LogoutHandler.post()` | 退出登录 | 已登录 |

---

## 安全机制

### 1. XSRF 防护

- 全局启用：`xsrf_cookies=True`
- 表单内置：`{% module xsrf_form_html() %}`
- Tornado 自动校验所有 POST 请求的 token

### 2. 密码加密

- **算法**：PBKDF2-HMAC-SHA256
- **迭代次数**：100,000 次
- **盐值**：16 字节随机盐（`secrets.token_bytes(16)`）
- **存储**：密码哈希 + 盐值分别存储

### 3. 安全 Cookie

- 使用 `set_secure_cookie()` 替代普通 cookie
- Cookie 内容经过签名防篡改
- 密钥配置：`cookie_secret="demo-cookie-secret-change-me"`

### 4. SQL 注入防护

- 所有 SQL 查询使用参数化语句（`?` 占位符）
- 示例：`conn.execute("SELECT ... WHERE username = ?", (username,))`

---

## 开发环境搭建

### 1. 创建虚拟环境

```bash
python -m venv venv
```

### 2. 激活虚拟环境

**Windows PowerShell：**
```powershell
.\venv\Scripts\Activate.ps1
```

**Windows CMD：**
```cmd
.\venv\Scripts\activate.bat
```

### 3. 安装依赖

```bash
pip install tornado==6.5.5
```

### 4. 启动服务

```bash
python app.py
```

服务默认监听端口：**10086**

访问地址：`http://127.0.0.1:10086/auth/login`

### 5. 创建初始管理员账号（首次运行）

```bash
python text.py
```

---

## Tornado 核心知识点

### 1. Application 配置

```python
settings = dict(
    template_path = os.path.join(base_url, "app", "templates"),  # 模板路径
    static_path = os.path.join(base_url, "app", "static"),       # 静态资源路径
    cookie_secret = "demo-cookie-secret-change-me",              # Cookie 签名密钥
    login_url = "/auth/login",                                    # 登录页 URL
    xsrf_cookies = True,                                          # 启用 XSRF 防护
    debug = True,                                                 # 开发模式
    autoreload = True                                             # 代码修改自动重载
)
```

### 2. Handler 路由注册

```python
tornado.web.Application([
    (r"/", IndexHandler),
    (r"/auth/login", LoginHandler),
    (r"/auth/logout", LogoutHandler)
], **settings)
```

### 3. HTTPServer 多进程部署

```python
server = HTTPServer(app)
server.bind(10086)
server.start()  # 自动根据 CPU 核心数启动多进程
```

### 4. IOLoop 事件循环

```python
tornado.ioloop.IOLoop.current().start()
```

---

## 数据库设计

### 当前表结构

**users 表** - 用户信息表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 用户 ID |
| username | TEXT | NOT NULL UNIQUE | 用户名（唯一） |
| password_hash | TEXT | NOT NULL | PBKDF2 加密后的密码哈希 |
| salt | TEXT | NOT NULL | 密码盐值（16进制字符串） |
| create_at | TEXT | DEFAULT(datetime('now')) | 创建时间 |

### 后续扩展建议

根据 AI 智能瞭望与智能问数系统的需求，可能需要新增以下数据表：

- `ai_tasks` - AI 任务记录表
- `data_sources` - 数据源配置表
- `query_logs` - 查询日志表
- `user_preferences` - 用户偏好设置表
- `chat_history` - 对话历史表

---

## 模板系统说明

### 模板继承

所有页面模板继承自 `base.html`，通过 `{% block body %}{% end %}` 注入内容。

**base.html 结构：**
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link rel="stylesheet" href="{{ static_url('css/base.css') }}">
    <script src="{{ static_url('js/base.js') }}"></script>
</head>
<body>
    <div class="container">
        {% block body %}{% end %}
    </div>
</body>
</html>
```

### 模板变量传递

Controller 中通过 `self.render("template.html", key=value)` 传递变量：

```python
self.render("login.html", title="登录", error=None)
self.render("index.html", title="后台", username=self.current_user)
```

---

## 代码规范与约定

### 1. 命名规范

- 文件名：蛇形命名（snake_case），如 `base.py`、`user.py`
- 类名：大驼峰命名（PascalCase），如 `BaseHandler`、`UserRepository`
- 方法名：蛇形命名（snake_case），如 `get_current_user()`、`verify_user()`
- 私有方法：前导下划线，如 `_hash_password()`、`_project_root()`

### 2. 类型注解

Model 层方法使用类型注解：
```python
def create_user(username: str, password: str) -> bool:
def get_user_by_username(username: str) -> dict | None:
```

### 3. 文档字符串

关键方法包含 docstring 说明：
```python
"""
创建新用户（用户名唯一）
:param username: 用户名
:param password: 原始密码
:return: 创建成功返回 True，用户名重复返回 False
"""
```

### 4. 异常处理

使用 try-except 捕获数据库异常：
```python
try:
    with get_connection() as conn:
        conn.execute("INSERT ...", (...))
    return True
except sqlite3.IntegrityError:
    return False
```

---

## 已知待完善项

### 1. 功能层面

- [ ] 注册功能（`register.html` 已创建但为空，`auth.py` 中无 RegisterHandler）
- [ ] 密码重置/修改功能
- [ ] 用户权限管理（角色/权限）
- [ ] 会话超时自动退出
- [ ] 记住我功能

### 2. 安全层面

- [ ] Cookie 密钥需从配置文件读取（当前硬编码）
- [ ] 增加密码强度校验
- [ ] 增加登录失败次数限制（防爆破）
- [ ] 增加 HTTPS 支持
- [ ] XSRF token 刷新机制

### 3. 代码层面

- [ ] `register.html` 模板为空，需补充
- [ ] `base.js` 脚本为空，需补充公共 JS
- [ ] 配置文件抽离（端口、密钥等）
- [ ] 日志系统接入
- [ ] 错误页面定制（404/500）

### 4. 测试层面

- [ ] 单元测试（`test.py` 已规划但未实现）
- [ ] 接口测试
- [ ] 前端 UI 测试

---

## 后续开发计划（AI 智能瞭望与智能问数系统）

### 阶段一：基础功能完善

1. 完善注册/密码修改功能
2. 用户信息管理页面
3. 系统设置页面
4. 日志记录功能

### 阶段二：AI 智能瞭望模块

1. AI 任务配置界面
2. 数据源接入管理
3. 智能监控规则配置
4. 告警通知机制
5. 瞭望报告生成

### 阶段三：智能问数模块

1. 自然语言查询输入框
2. AI 语义解析引擎接入
3. 查询结果可视化展示
4. 历史查询记录
5. 常用查询模板

### 阶段四：系统集成与优化

1. 多数据源支持（MySQL/PostgreSQL/API）
2. 缓存机制（Redis）
3. 性能优化（分页/索引）
4. 权限细粒度控制
5. 数据导出功能

### ✅ 智慧舆情数智大屏（已完成）

1. **后端数据接口** — 4个API接口：统计(/api/screen/stats)、词云(/api/screen/wordcloud)、地球数据(/api/screen/earth-data)、智能分析(/api/screen/analyze)
2. **词云图** — echarts-wordcloud 可视化，点击词条弹出关联瞭望数据标题列表
3. **统计图表** — 采集量与消息量双系列趋势图，支持折线图/柱状图切换
4. **3D地球** — echarts-gl globe球体 + Canvas动态纹理，世界地图+中国省份边界紧贴球面
5. **AI智能分析** — 聊天内容违规检测与话题提炼，缓存1小时，审计日志记录
6. **性能优化** — DB索引、词云异步预计算缓存、超时兜底
7. **新增大屏菜单** — 自动插入"数智大屏→大屏展示"到管理后台菜单

---

## 常见问题

### Q1: 如何修改服务端口？

修改 `app.py` 中的 `server.bind(10086)` 为其他端口即可。

### Q2: 如何重置管理员密码？

删除 `database/app.db` 文件，重新启动服务后运行 `python text.py` 重新创建。

### Q3: 如何关闭调试模式？

修改 `app.py` 中的 `debug=True` 为 `debug=False`，并关闭 `autoreload=True`。

### Q4: 数据库文件在哪里？

位于 `database/app.db`，由 `init_db()` 自动创建。

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v0.1.0 | 2026-05-23 | 初始版本，完成基础框架搭建和登录功能 |

---

## 技术参考

- [Tornado 官方文档](https://www.tornadoweb.org/)
- [Tornado Template 语法](https://www.tornadoweb.org/en/stable/template.html)
- [SQLite3 Python API](https://docs.python.org/3/library/sqlite3.html)
- [PBKDF2 密码加密](https://docs.python.org/3/library/hashlib.html#hashlib.pbkdf2_hmac)
