# 项目目录结构说明

## 根目录文件
- `app.md`：本文件，说明整个项目的目录结构及文件归属，是指导AI完成开发的重要框架性帮助文件
- `app.py`：整个程序的主入口，采用 Tornado 框架构建实现，MVC 三层经典架构
- `test.py`：程序单元测试用脚本文件，主要用于模块/包/方法的测试，可以写入一些临时性的测试用例

---

## 主包：`app/`
整个项目的主包

- `__init__.py`：Python 包标识文件

### `app/controllers/`（MVC 控制层模块）
- `auth.py`：鉴权相关的控制层方法，涉及登录、注册、退出
- `base.py`：控制层公共基类，提供统一的登录态获取
- `home.py`：首页相关控制逻辑
- `__init__.py`：模块初始化文件
- `__pycache__/`：Python 自动生成的字节码缓存目录
  - `auth.cpython-311.pyc`
  - `base.cpython-311.pyc`
  - `home.cpython-311.pyc`
  - `__init__.cpython-311.pyc`

### `app/models/`（业务与数据模型层）
- `db.py`：SQLite 数据库访问层 Model，后续可拓展兼容 MySQL/PostgreSQL 等数据库访问逻辑
- `user.py`：对应用户相关的 Model
- `__init__.py`：模块初始化文件
- `__pycache__/`：Python 自动生成的字节码缓存目录
  - `db.cpython-311.pyc`
  - `user.cpython-311.pyc`
  - `__init__.cpython-311.pyc`

### `app/static/`（视图层静态资源）
- `css/`（样式文件）
  - `base.css`：基础公共样式
- `js/`（JS 脚本文件）
  - `base.js`：基础公共脚本

### `app/templates/`（视图层模板文件）
- `base.html`：基础公共模板
- `index.html`：后台首页模板
- `login.html`：登录页模板
- `register.html`：注册页模板
- `__pycache__/`：Python 自动生成的字节码缓存目录
  - `__init__.cpython-311.pyc`

---

## `database/`（SQLite 数据库目录）
用于存放 SQLite 文件或 SQL 脚本文件
- `app.db`：当前自动创建的 SQLite 数据库，通过 `init_db()` 在启动时检查创建

---

## `venv/`（Python 虚拟环境）
Python 3.11 下创建的虚拟环境
- 创建命令：`python -m venv venv`
- 后续开发、运行启动需在此虚拟环境中完成