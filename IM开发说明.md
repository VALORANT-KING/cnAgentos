# 团队任务 2：仿微信即时通信 — 开发说明

> 版本：2026-05-24 | 基于 `requirements.md` 团队任务 2 实现

---

## 一、做了什么

在现有 Tornado 项目上，按 `requirements.md` 补齐了**用户侧即时通信**能力：后端以 **HTTP API + WebSocket** 为主，前端完成页面与交互。

### 1.1 后端

| 模块 | 说明 |
|------|------|
| **数据库** | 在 `app/models/db.py` 增加表：`im_friends`、`im_friend_requests`、`im_groups`、`im_group_members`、`im_messages`、`im_files`、`im_servers`，并插入默认本机服务器记录 |
| **Model** | `app/models/im_friend.py`、`im_group.py`、`im_message.py`、`im_file.py`（含 `ImServerRepository`） |
| **Controller** | `app/controllers/im.py`：REST 接口 + `/ws/im` 实时推送、群聊 @数字员工 自动回复（复用问数侧 AI/API 逻辑） |
| **路由** | 在 `app.py` 注册全部 IM 路由；服务监听改为 `0.0.0.0:10086`（局域网可访问） |

### 1.2 前端

| 文件 | 说明 |
|------|------|
| `app/templates/home.html` | 登录后入口：智能问数 / 智能聊天 |
| `app/templates/im_index.html` | 智能聊天主界面 |
| `app/static/css/im.css` | 即时通信样式 |
| `app/static/js/im.js` | WebSocket、通讯录、聊天、文件、服务器切换 |
| `app/templates/chat.html` | 增加跳转「首页」「智能聊天」 |
| `app/controllers/home.py` | 新增 `HomePortalHandler`（`/home`） |
| `app/controllers/auth.py` | 登录/注册后跳转 `/home`（原为 `/chat`） |

### 1.3 功能覆盖

- 用户侧主界面：`/home` 切换「智能问数」「智能聊天」
- 通讯录：好友列表、群列表、在线搜索用户、发送/通过/拒绝好友申请
- 1v1 私聊：消息气泡、文本、Emoji、动态表情、文件上传/下载
- 群聊：创建群、拉好友入群、群内消息、@数字员工
- 实时性：WebSocket 推送 + 断线重连
- 多服务器：列表、健康检查、前端自动/手动切换
- 数字员工：群聊/私聊 @别名 或调用 `/api/im/employee/call`

### 1.4 消息类型（`im_messages.msg_type`）

| 类型 | 说明 |
|------|------|
| `text` | 纯文本 |
| `emoji` | Emoji |
| `sticker` | 动态表情（前端 CSS 动画，无外链 CDN） |
| `file` | 文件消息（关联 `im_files.id`） |
| `employee_call` | 数字员工回复 |

### 1.5 文件存储

- 上传目录：`uploads/im/`（按 MD5 去重）
- 已在 `.gitignore` 中忽略 `uploads/`

---

## 二、产生的接口一览

### 2.1 页面路由（需登录）

| 路径 | 方法 | 说明 |
|------|------|------|
| `/home` | GET | 子系统选择首页（智能问数 / 智能聊天） |
| `/im` | GET | 智能聊天主界面 |

登录/注册成功后默认跳转：`/home`。

---

### 2.2 WebSocket

| 路径 | 说明 |
|------|------|
| `ws://{host}/ws/im` | 实时收发消息；需携带登录 Cookie |

#### 客户端 → 服务端

```json
{
  "type": "message",
  "receiver_type": "user",
  "receiver_id": 123,
  "msg_type": "text",
  "content": "消息内容",
  "file_id": 0,
  "employee_calls": [
    { "alias": "@天气", "param": "北京" }
  ]
}
```

| 字段 | 说明 |
|------|------|
| `type` | `message` 发送消息；`ping` 心跳 |
| `receiver_type` | `user` 私聊 / `group` 群聊 |
| `receiver_id` | 对方用户 ID 或群 ID |
| `msg_type` | `text` / `file` / `sticker` / `emoji` |
| `employee_calls` | 可选；群聊 @数字员工时由前端解析传入 |

#### 服务端 → 客户端

| type | 说明 |
|------|------|
| `connected` | 连接成功，含 `user_id`、`username` |
| `message` | 新消息，`data` 为消息对象 |
| `friend_accepted` | 好友申请已通过 |
| `group_invite` | 被邀请入群 |
| `pong` | 响应 `ping` |
| `error` | 错误提示 |

---

### 2.3 HTTP API（即时通信）

**通用约定：**

- 响应格式：`{ "code": 0|1, "msg": "...", "data": ... }`（部分列表带 `count`）
- `code === 0` 表示成功
- 除健康检查外均需登录（`username` Cookie）
- POST 请求须携带 XSRF：表单 `_xsrf` 或请求头 `X-XSRFToken`

#### 好友 / 通讯录

| 路径 | 方法 | 参数 | 说明 |
|------|------|------|------|
| `/api/im/friends/search` | GET | `keyword` | 按用户名模糊搜索用户 |
| `/api/im/friends/add` | POST | `friend_id`, `message`（可选） | 发送好友申请 |
| `/api/im/friends/list` | GET | — | 当前用户好友列表 |
| `/api/im/friends/requests` | GET | — | 待处理申请（incoming）与已发出（outgoing） |
| `/api/im/friends/accept` | POST | `request_id` | 同意好友申请 |
| `/api/im/friends/reject` | POST | `request_id` | 拒绝好友申请 |

#### 群组

| 路径 | 方法 | 参数 | 说明 |
|------|------|------|------|
| `/api/im/groups/create` | POST | `name`, `member_ids`（JSON 数组字符串，如 `"[2,3]"`） | 创建群并邀请成员 |
| `/api/im/groups/list` | GET | — | 当前用户加入的群列表 |
| `/api/im/groups/join` | POST | `group_id` | 加入群组 |
| `/api/im/groups/members` | GET | `group_id` | 群成员列表 |
| `/api/im/groups/invite` | POST | `group_id`, `member_ids`（JSON 数组字符串） | 邀请好友入群 |

#### 消息 / 会话

| 路径 | 方法 | 参数 | 说明 |
|------|------|------|------|
| `/api/im/messages/history` | GET | `receiver_type`, `receiver_id`, `before_id`（可选，分页） | 历史消息；`data.messages` + `data.employees` |
| `/api/im/conversations` | GET | — | 最近会话摘要列表 |

#### 文件

| 路径 | 方法 | 参数 | 说明 |
|------|------|------|------|
| `/api/im/files/upload` | POST | `multipart/form-data`，字段名 `file` | 上传文件；返回 `id`、`file_name`、`file_size` |
| `/api/im/files/download` | GET | `id` | 下载文件（附件流） |

#### 服务器 / 数字员工

| 路径 | 方法 | 参数 | 说明 |
|------|------|------|------|
| `/api/im/servers/list` | GET | — | 聊天服务器配置列表（表 `im_servers`） |
| `/api/im/health` | GET | — | 健康检查，**无需登录**；返回 `{ "code": 0, "status": "online" }` |
| `/api/im/employee/call` | POST | `alias`, `param`, `receiver_type`, `receiver_id` | 显式调用数字员工，写入消息并 WebSocket 推送 |

---

### 2.4 复用的已有接口（问数 / 数字员工）

| 路径 | 方法 | 用途 |
|------|------|------|
| `/api/employee/list` | GET | IM 页加载可 @ 的数字员工列表 |

数字员工业务能力依赖表 `digital_employees` 及关联的模型引擎 / `api_services`，逻辑与任务八智能问数一致。

---

## 三、数据库表（新增）

```sql
-- 好友关系（status: 1=好友, 0=已解除）
im_friends(user_id, friend_id, remark, status, create_at)

-- 好友申请（status: 0=待处理, 1=已同意, 2=已拒绝）
im_friend_requests(from_user_id, to_user_id, message, status, create_at)

-- 群组
im_groups(name, owner_id, announcement, status, create_at)

-- 群成员（role: owner / admin / member）
im_group_members(group_id, user_id, role, create_at)

-- 聊天消息
im_messages(msg_type, content, file_path, file_id, sender_id,
            receiver_type, receiver_id, employee_id, create_at)

-- 文件（file_hash 去重）
im_files(file_name, file_path, file_size, file_hash, uploader_id, create_at)

-- 聊天服务器配置（多机切换）
im_servers(name, host, port, status, current_load, create_at)
```

---

## 四、关键文件清单

```
cnAgentos/
├── IM开发说明.md                 # 本文件
├── app.py                        # IM 路由注册，0.0.0.0:10086
├── uploads/im/                   # 聊天文件存储（运行时生成）
├── app/
│   ├── controllers/
│   │   ├── im.py                 # WebSocket + HTTP Handler
│   │   └── home.py               # /home 入口
│   ├── models/
│   │   ├── im_friend.py
│   │   ├── im_group.py
│   │   ├── im_message.py
│   │   ├── im_file.py
│   │   └── db.py                 # 建表
│   ├── templates/
│   │   ├── home.html
│   │   └── im_index.html
│   └── static/
│       ├── css/im.css
│       └── js/im.js
```

---

## 五、部署与使用

### 5.1 启动服务

```bash
python app.py
```

### 5.2 访问地址

| 场景 | 地址 |
|------|------|
| 本机 | http://127.0.0.1:10086/home |
| 局域网 | http://\<本机局域网IP\>:10086/home |
| 智能聊天 | http://127.0.0.1:10086/im |
| 智能问数 | http://127.0.0.1:10086/chat |

### 5.3 局域网联调步骤

1. 各端注册不同账号
2. 进入「智能聊天」→ 好友 Tab → 搜索用户名 → 发送申请
3. 对方在「申请」中同意
4. 会话列表选择好友私聊，或建群后群聊
5. 群聊输入 `@川小农` / `@天气 北京` 等触发数字员工

### 5.4 多服务器切换

- 默认 `im_servers` 有一条 `127.0.0.1:10086`
- 局域网场景建议在库中增加条目：`host` 填服务器局域网 IP
- 前端左下角下拉切换；不可用时自动探测 `/api/im/health` 并尝试下一台

---

## 六、尚未实现（requirements 中有规划）

以下管理端功能在需求文档中有描述，**本轮未实现页面与路由**：

| 规划路径 | 说明 |
|----------|------|
| `/admin/im/groups` | 后台群管理 |
| `/admin/im/files` | 后台文件管理 |
| `/admin/im/servers` | 后台服务器管理 |

用户侧已具备 `im_servers` 表及 `GET /api/im/servers/list`，可与成员 B 的服务器配置 API 对接扩展。

---

## 七、与 requirements.md 对照

| 需求项 | 状态 |
|--------|------|
| 主界面切换问数/聊天 | ✅ `/home` |
| 好友列表、群列表 | ✅ |
| 在线查找用户、好友申请 | ✅ |
| 1v1 私聊（文本/表情/文件） | ✅ |
| 群聊、拉人、@数字员工 | ✅ |
| WebSocket 实时推送 | ✅ |
| 多服务器切换 | ✅（用户侧 API + 前端） |
| 数字员工 API 对接 | ✅（复用问数逻辑） |
| 管理端群/文件/服务器管理 | ⬜ 待开发 |

---

> 文档维护：团队任务 2 即时通信模块
