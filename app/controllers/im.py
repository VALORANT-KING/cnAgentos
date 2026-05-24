import json
import os
import random
import re
import urllib.parse
import tornado.web
import tornado.ioloop
import tornado.websocket

from app.controllers.base import BaseHandler
from app.controllers.chat import (
    _resolve_employee_alias,
    _parse_employee_call,
    _call_api_employee,
)
from app.models.user import UserRepository
from app.models.im_friend import ImFriendRepository
from app.models.im_group import ImGroupRepository
from app.models.im_message import ImMessageRepository
from app.models.im_file import ImFileRepository, ImServerRepository
from app.models.digital_employee import DigitalEmployeeRepository
from app.models.model_engine import ModelEngineRepository
from app.models.employee_tool import EmployeeToolRepository


# 毒鸡汤语录库
TOXIC_SOUP_QUOTES = [
    "你以为有钱人很快乐吗？他们的快乐你根本想象不到。",
    "条条大路通罗马，而有些人就生在罗马。",
    "比一个人吃火锅更孤单的，是一个人没有钱吃火锅。",
    "你努力过后才发现，智商的鸿沟是无法逾越的。",
    "失败并不可怕，可怕的是你还相信这句话。",
    "你总嫌有些人懒，说得好像你勤快了就一定会成功一样。",
    "当你觉得自己又丑又穷，一无是处时，别绝望，至少你的判断是对的。",
    "生活不止眼前的苟且，还有读不懂的诗和到不了的远方。",
    "上帝是公平的，给了你丑的外表，还会给你低的智商，以免你显得太不协调。",
    "如果生活欺骗了你，不要悲伤，不要心急，多被骗几次就好了。",
    "你全力做到最好，可能还不如别人的随便搞搞。",
    "有些人出现在你的生命里，是为了告诉你：你真好骗。",
    "你努力赚钱的样子，真像个小丑。",
    "不要看轻自己，在这个世上，你最多只能排第二。",
    "比你优秀的人还在努力，那你努力有什么用？",
    "当你觉得自己怀才不遇时，请想想是不是少了才华。",
    "生活就像心电图，一帆风顺说明你已经挂了。",
    "你所谓的迷茫，不过是才华配不上梦想罢了。",
    "如果所有人都理解你，那你得普通成什么样。",
    "你认真做事的样子，真像在做无用功。",
]


# WebSocket 在线连接：user_id -> set(handler)
IM_ONLINE = {}


def _get_user_from_handler(handler):
    username = handler.get_secure_cookie("username")
    if not username:
        return None
    return UserRepository.get_user_by_username(username.decode("utf-8"))


def _register_online(user_id, ws):
    if user_id not in IM_ONLINE:
        IM_ONLINE[user_id] = set()
    IM_ONLINE[user_id].add(ws)


def _unregister_online(user_id, ws):
    if user_id in IM_ONLINE:
        IM_ONLINE[user_id].discard(ws)
        if not IM_ONLINE[user_id]:
            del IM_ONLINE[user_id]


def broadcast_user(user_id, payload):
    data = json.dumps(payload, ensure_ascii=False)
    for ws in list(IM_ONLINE.get(user_id, [])):
        try:
            ws.write_message(data)
        except Exception:
            pass


def broadcast_group(group_id, payload, exclude_user_id=None):
    member_ids = ImGroupRepository.get_member_ids(group_id)
    for uid in member_ids:
        if exclude_user_id and uid == exclude_user_id:
            continue
        broadcast_user(uid, payload)


def _file_content_disposition(filename):
    """生成兼容中文文件名的 Content-Disposition（HTTP 头仅支持 latin-1）"""
    ascii_name = filename.encode("ascii", "ignore").decode() or "download"
    utf8_name = urllib.parse.quote(filename)
    return f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{utf8_name}'


def _normalize_message(msg):
    """WebSocket/JSON 序列化前规范化消息字段"""
    if not msg:
        return msg
    out = dict(msg)
    for key in ("id", "sender_id", "receiver_id", "file_id", "employee_id"):
        if key in out and out[key] is not None:
            out[key] = int(out[key])
    return out


def _message_payload(msg):
    return {"type": "message", "data": _normalize_message(msg)}


def parse_employee_mentions(content):
    """解析消息中的 @数字员工"""
    employees = DigitalEmployeeRepository.get_all()
    if not employees:
        return []
    found = []
    sorted_emps = sorted(employees, key=lambda e: len(e.get("alias", "")), reverse=True)
    remaining = content
    for emp in sorted_emps:
        alias = emp.get("alias", "")
        if not alias or alias not in remaining:
            continue
        idx = remaining.find(alias)
        after = remaining[idx + len(alias):].lstrip("：: \t")
        param = ""
        if after:
            m = re.match(r"^(\S+)", after)
            if m:
                param = m.group(1)
        found.append({"employee": emp, "alias": alias, "param": param})
        remaining = remaining.replace(alias, "", 1)
    return found


def _call_local_employee(employee):
    """本地内置数字员工（毒鸡汤等）"""
    alias = employee.get("alias", "")
    if alias == "@毒鸡汤" or employee.get("name") == "毒鸡汤":
        quote = random.choice(TOXIC_SOUP_QUOTES)
        return json.dumps({
            "_im_card": "toxic_soup",
            "quote": quote,
            "title": "今日毒鸡汤",
        }, ensure_ascii=False)
    return f"本地员工 {employee.get('name')} 暂无可用功能"


def _call_weather_for_im(employee, param):
    """天气 API 返回 IM 卡片 JSON（含前端特效联动数据）"""
    import requests
    try:
        api_id = employee.get("api_service_id", 0)
        if not api_id:
            return "❌ 天气员工未关联 API 服务"
        from app.models.api_service import ApiServiceRepository
        api = ApiServiceRepository.get_by_id(api_id)
        if not api:
            return "❌ 天气 API 服务不存在"
        city = param or "北京"
        url = api["url"]
        if "{city}" in url:
            url = url.replace("{city}", urllib.parse.quote(city))
        else:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}city={urllib.parse.quote(city)}"
        safe_headers = {"accept-encoding": "gzip, deflate", "user-agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=safe_headers, timeout=10, verify=False)
        if resp.status_code != 200:
            return f"❌ 天气 API 请求失败 (HTTP {resp.status_code})"
        raw = resp.json()
        data = raw.get("data", raw)
        weather = data.get("weather", "")
        effect = "default"
        for kw, fx in [("晴", "sunny"), ("雨", "rain"), ("雪", "snow"), ("雾", "fog"), ("云", "cloudy")]:
            if kw in weather:
                effect = fx
                break
        card = {
            "_im_card": "weather",
            "city": data.get("city", city),
            "weather": weather,
            "temp": data.get("temp", ""),
            "tempn": data.get("tempn", ""),
            "wind": data.get("wind", ""),
            "effect": effect,
            "humidity": data.get("current", {}).get("humidity", ""),
            "air": data.get("current", {}).get("air", ""),
            "time": data.get("current", {}).get("time", data.get("time", "")),
        }
        return json.dumps(card, ensure_ascii=False)
    except Exception as e:
        return f"❌ 天气查询出错: {str(e)}"


def _build_ai_messages(employee, user_content, user_id, receiver_type, receiver_id):
    """构建 AI 多轮对话 messages 列表"""
    prompt = employee.get("prompt", "")
    tools = EmployeeToolRepository.get_bindings(employee["id"])
    if tools:
        tool_desc = "；".join([t["name"] + ": " + (t.get("description") or "") for t in tools])
        prompt += f"\n\n你可使用的工具：{tool_desc}"

    messages = [{"role": "system", "content": prompt}]
    history = ImMessageRepository.get_ai_context(user_id, receiver_type, receiver_id, limit=8)
    for msg in history:
        if msg.get("msg_type") == "employee_call" or msg.get("sender_id") == 0:
            messages.append({"role": "assistant", "content": msg.get("content", "")})
        else:
            text = msg.get("content", "")
            for emp in DigitalEmployeeRepository.get_all():
                alias = emp.get("alias", "")
                if alias and alias in text:
                    text = text.replace(alias, "").strip("：: \t")
            if text:
                messages.append({"role": "user", "content": text})
    messages.append({"role": "user", "content": user_content or "你好"})
    return messages


def call_employee_reply(employee, param, user_id=0, receiver_type="group", receiver_id=0):
    if employee.get("status") != 1:
        return f"数字员工 {employee.get('name')} 已禁用"

    agent_type = employee.get("agent_type", "")

    if agent_type == "local":
        return _call_local_employee(employee)

    if employee["category"] == "AI" and agent_type == "chat":
        model = ModelEngineRepository.get_default()
        if not model:
            return "系统未配置默认模型"
        user_content = param or "你好"
        try:
            from openai import OpenAI
            import httpx
            client = OpenAI(
                api_key=model.get("api_key") or "sk-no-key-required",
                base_url=model.get("base_url") or "https://api.openai.com/v1",
                http_client=httpx.Client(timeout=httpx.Timeout(30.0, connect=5.0)),
            )
            messages = _build_ai_messages(
                employee, user_content, user_id, receiver_type, receiver_id
            )
            resp = client.chat.completions.create(
                model=model.get("model_name") or "gpt-3.5-turbo",
                messages=messages,
                max_tokens=model.get("max_tokens", 2048),
                temperature=model.get("temperature", 0.7),
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"AI 调用出错: {str(e)}"

    if employee["category"] == "普通" and agent_type == "api":
        if employee.get("alias") == "@天气" or employee.get("name") == "天气":
            return _call_weather_for_im(employee, param)
        return _call_api_employee(employee, param)

    return f"不支持的数字员工类型: {employee.get('name')}"


class ImBaseHandler(BaseHandler):
    def get_login_url(self):
        return "/auth/login"

    def _current_user_dict(self):
        username = self.current_user
        if not username:
            return None
        return UserRepository.get_user_by_username(username)

    def write_json(self, code=0, msg="", data=None, count=None):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        body = {"code": code, "msg": msg}
        if data is not None:
            body["data"] = data
        if count is not None:
            body["count"] = count
        self.write(json.dumps(body, ensure_ascii=False))


class ImIndexHandler(ImBaseHandler):
    @tornado.web.authenticated
    def get(self):
        user = self._current_user_dict()
        self.render(
            "im_index.html",
            username=user["username"] if user else "",
            user_id=user["id"] if user else 0,
        )


class ImFriendSearchHandler(ImBaseHandler):
    @tornado.web.authenticated
    def get(self):
        user = self._current_user_dict()
        if not user:
            return self.write_json(1, "用户不存在")
        keyword = self.get_argument("keyword", "")
        users = ImFriendRepository.search_users(keyword, user["id"])
        return self.write_json(0, "", users)


class ImFriendAddHandler(ImBaseHandler):
    @tornado.web.authenticated
    def post(self):
        user = self._current_user_dict()
        if not user:
            return self.write_json(1, "用户不存在")
        friend_id = int(self.get_body_argument("friend_id", 0))
        message = self.get_body_argument("message", "")
        if not friend_id:
            return self.write_json(1, "参数错误")
        ok, msg, request_id = ImFriendRepository.send_request(user["id"], friend_id, message)
        if ok:
            broadcast_user(friend_id, {
                "type": "friend_request",
                "request_id": request_id,
                "from_user_id": user["id"],
                "from_username": user["username"],
                "message": message,
            })
        return self.write_json(0 if ok else 1, msg)


class ImFriendListHandler(ImBaseHandler):
    @tornado.web.authenticated
    def get(self):
        user = self._current_user_dict()
        if not user:
            return self.write_json(1, "用户不存在")
        friends = ImFriendRepository.get_friends(user["id"])
        return self.write_json(0, "", friends)


class ImFriendRequestsHandler(ImBaseHandler):
    @tornado.web.authenticated
    def get(self):
        user = self._current_user_dict()
        if not user:
            return self.write_json(1, "用户不存在")
        incoming = ImFriendRepository.get_pending_requests(user["id"])
        outgoing = ImFriendRepository.get_sent_requests(user["id"])
        return self.write_json(0, "", {"incoming": incoming, "outgoing": outgoing})


class ImFriendAcceptHandler(ImBaseHandler):
    @tornado.web.authenticated
    def post(self):
        user = self._current_user_dict()
        if not user:
            return self.write_json(1, "用户不存在")
        request_id = int(self.get_body_argument("request_id", 0))
        ok, msg = ImFriendRepository.accept_request(request_id, user["id"])
        if ok:
            from app.models.db import get_connection
            with get_connection() as conn:
                req_row = conn.execute(
                    "SELECT from_user_id FROM im_friend_requests WHERE id = ?",
                    (request_id,),
                ).fetchone()
            if req_row:
                broadcast_user(req_row["from_user_id"], {
                    "type": "friend_accepted",
                    "user_id": user["id"],
                    "username": user["username"],
                })
        return self.write_json(0 if ok else 1, msg)


class ImFriendRejectHandler(ImBaseHandler):
    @tornado.web.authenticated
    def post(self):
        user = self._current_user_dict()
        if not user:
            return self.write_json(1, "用户不存在")
        request_id = int(self.get_body_argument("request_id", 0))
        ok, msg = ImFriendRepository.reject_request(request_id, user["id"])
        return self.write_json(0 if ok else 1, msg)


class ImFriendDeleteHandler(ImBaseHandler):
    @tornado.web.authenticated
    def post(self):
        user = self._current_user_dict()
        if not user:
            return self.write_json(1, "用户不存在")
        friend_id = int(self.get_body_argument("friend_id", 0))
        if not friend_id:
            return self.write_json(1, "参数错误")
        ok, msg = ImFriendRepository.remove_friend(user["id"], friend_id)
        return self.write_json(0 if ok else 1, msg)


class ImGroupCreateHandler(ImBaseHandler):
    @tornado.web.authenticated
    def post(self):
        user = self._current_user_dict()
        if not user:
            return self.write_json(1, "用户不存在")
        name = (self.get_body_argument("name", "") or "").strip()
        member_ids_raw = self.get_body_argument("member_ids", "[]")
        employee_ids_raw = self.get_body_argument("employee_ids", "[]")
        if not name:
            return self.write_json(1, "群名称不能为空")
        try:
            member_ids = json.loads(member_ids_raw)
            member_ids = [int(x) for x in member_ids if int(x) != user["id"]]
        except Exception:
            member_ids = []
        try:
            employee_ids = [int(x) for x in json.loads(employee_ids_raw)]
        except Exception:
            employee_ids = []
        group_id = ImGroupRepository.create(
            name, user["id"], member_ids, employee_ids
        )
        group = ImGroupRepository.get_by_id(group_id)
        return self.write_json(0, "创建成功", group)


class ImGroupListHandler(ImBaseHandler):
    @tornado.web.authenticated
    def get(self):
        user = self._current_user_dict()
        if not user:
            return self.write_json(1, "用户不存在")
        groups = ImGroupRepository.get_user_groups(user["id"])
        return self.write_json(0, "", groups)


class ImGroupJoinHandler(ImBaseHandler):
    @tornado.web.authenticated
    def post(self):
        user = self._current_user_dict()
        if not user:
            return self.write_json(1, "用户不存在")
        group_id = int(self.get_body_argument("group_id", 0))
        ok, msg = ImGroupRepository.join_group(group_id, user["id"])
        return self.write_json(0 if ok else 1, msg)


class ImGroupMembersHandler(ImBaseHandler):
    @tornado.web.authenticated
    def get(self):
        group_id = int(self.get_argument("group_id", 0))
        if not group_id:
            return self.write_json(1, "参数错误")
        group = ImGroupRepository.get_group_detail(group_id)
        if not group:
            return self.write_json(1, "群组不存在或已封禁")
        members = ImGroupRepository.get_members(group_id)
        employees = ImGroupRepository.get_employees(group_id)
        return self.write_json(0, "", {
            "group": group,
            "members": members,
            "employees": employees,
        })


class ImGroupInviteHandler(ImBaseHandler):
    @tornado.web.authenticated
    def post(self):
        user = self._current_user_dict()
        if not user:
            return self.write_json(1, "用户不存在")
        group_id = int(self.get_body_argument("group_id", 0))
        member_ids_raw = self.get_body_argument("member_ids", "[]")
        employee_ids_raw = self.get_body_argument("employee_ids", "[]")
        try:
            member_ids = [int(x) for x in json.loads(member_ids_raw)]
        except Exception:
            member_ids = []
        try:
            employee_ids = [int(x) for x in json.loads(employee_ids_raw)]
        except Exception:
            employee_ids = []
        if not member_ids and not employee_ids:
            return self.write_json(1, "请选择要邀请的成员")
        ok, msg = True, "操作成功"
        if member_ids:
            ok, msg = ImGroupRepository.add_members(group_id, user["id"], member_ids)
        if ok and employee_ids:
            ok, msg = ImGroupRepository.add_employees(group_id, user["id"], employee_ids)
        if ok:
            for uid in member_ids:
                broadcast_user(uid, {
                    "type": "group_invite",
                    "group_id": group_id,
                })
        return self.write_json(0 if ok else 1, msg)


class ImMessageHistoryHandler(ImBaseHandler):
    @tornado.web.authenticated
    def get(self):
        user = self._current_user_dict()
        if not user:
            return self.write_json(1, "用户不存在")
        receiver_type = self.get_argument("receiver_type", "user")
        receiver_id = int(self.get_argument("receiver_id", 0))
        before_id = int(self.get_argument("before_id", 0))
        if not receiver_id:
            return self.write_json(1, "参数错误")
        if receiver_type == "user":
            if not ImFriendRepository.is_friend(user["id"], receiver_id) and receiver_id != user["id"]:
                return self.write_json(1, "非好友无法查看消息")
        elif receiver_type == "group":
            if not ImGroupRepository.is_member(receiver_id, user["id"]):
                return self.write_json(1, "非群成员")
        messages = ImMessageRepository.get_history(
            user["id"], receiver_type, receiver_id, before_id=before_id
        )
        messages = [_normalize_message(m) for m in messages]
        employees = DigitalEmployeeRepository.get_all()
        return self.write_json(0, "", {"messages": messages, "employees": employees})


class ImConversationsHandler(ImBaseHandler):
    @tornado.web.authenticated
    def get(self):
        user = self._current_user_dict()
        if not user:
            return self.write_json(1, "用户不存在")
        convs = ImMessageRepository.get_recent_conversations(user["id"])
        return self.write_json(0, "", convs)


class ImFileUploadHandler(ImBaseHandler):
    @tornado.web.authenticated
    def post(self):
        user = self._current_user_dict()
        if not user:
            return self.write_json(1, "用户不存在")
        if not self.request.files.get("file"):
            return self.write_json(1, "未选择文件")
        file_info = self.request.files["file"][0]
        record = ImFileRepository.save_file(
            file_info["filename"],
            file_info["body"],
            user["id"],
        )
        if not record:
            return self.write_json(1, "文件保存失败")
        return self.write_json(0, "上传成功", {
            "id": record["id"],
            "file_name": record["file_name"],
            "file_size": record.get("file_size", 0),
        })


class ImFileDownloadHandler(ImBaseHandler):
    @tornado.web.authenticated
    def get(self):
        file_id = int(self.get_argument("id", 0))
        if not file_id:
            self.set_status(400)
            return self.write("参数错误")
        record = ImFileRepository.get_by_id(file_id)
        if not record:
            self.set_status(404)
            return self.write("文件不存在")
        path = ImFileRepository.get_full_path(record)
        if not os.path.exists(path):
            self.set_status(404)
            return self.write("文件不存在")
        filename = record["file_name"]
        self.set_header("Content-Type", "application/octet-stream")
        self.set_header("Content-Disposition", _file_content_disposition(filename))
        with open(path, "rb") as f:
            data = f.read()
        self.set_header("Content-Length", str(len(data)))
        self.write(data)


class ImServerListHandler(ImBaseHandler):
    @tornado.web.authenticated
    def get(self):
        servers = ImServerRepository.get_active_servers()
        return self.write_json(0, "", servers)


class ImServerHealthHandler(tornado.web.RequestHandler):
    """服务器健康检查（无需登录，供前端切换探测）"""

    def get(self):
        self.write({"code": 0, "msg": "ok", "status": "online"})


class ImEmployeeListHandler(ImBaseHandler):
    @tornado.web.authenticated
    def get(self):
        employees = DigitalEmployeeRepository.get_all()
        return self.write_json(0, "", employees)


class ImEmployeeCallHandler(ImBaseHandler):
    @tornado.web.authenticated
    async def post(self):
        user = self._current_user_dict()
        if not user:
            return self.write_json(1, "用户不存在")
        alias = self.get_body_argument("alias", "")
        param = self.get_body_argument("param", "")
        receiver_type = self.get_body_argument("receiver_type", "user")
        receiver_id = int(self.get_body_argument("receiver_id", 0))

        employee = DigitalEmployeeRepository.get_by_alias(alias)
        if not employee:
            return self.write_json(1, f"未找到数字员工 {alias}")

        reply = call_employee_reply(
            employee, param, user["id"], receiver_type, receiver_id
        )
        msg = ImMessageRepository.add(
            user["id"], receiver_type, receiver_id, reply,
            msg_type="employee_call", employee_id=employee["id"],
        )
        payload = {"type": "message", "data": msg}
        if receiver_type == "user":
            broadcast_user(receiver_id, payload)
        else:
            broadcast_group(receiver_id, payload)
        broadcast_user(user["id"], payload)
        return self.write_json(0, "", msg)


class ImWebSocketHandler(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        self.user = _get_user_from_handler(self)
        if not self.user:
            self.close(4001, "未登录")
            return
        _register_online(self.user["id"], self)
        self.write_message(json.dumps({
            "type": "connected",
            "user_id": self.user["id"],
            "username": self.user["username"],
        }, ensure_ascii=False))

    def on_close(self):
        if getattr(self, "user", None):
            _unregister_online(self.user["id"], self)

    def on_message(self, message):
        if not getattr(self, "user", None):
            return
        try:
            data = json.loads(message)
        except Exception:
            return

        msg_type = data.get("type", "message")
        if msg_type == "ping":
            self.write_message(json.dumps({"type": "pong"}))
            return

        if msg_type != "message":
            return

        receiver_type = data.get("receiver_type", "user")
        receiver_id = int(data.get("receiver_id", 0))
        content = (data.get("content") or "").strip()
        message_kind = data.get("msg_type", "text")
        file_id = int(data.get("file_id", 0))
        file_path = data.get("file_path", "")

        if not receiver_id:
            return

        if message_kind == "file" and file_id:
            record = ImFileRepository.get_by_id(file_id)
            if not record:
                self.write_message(json.dumps({
                    "type": "error", "msg": "文件不存在或已删除",
                }, ensure_ascii=False))
                return
            file_path = record.get("file_path", "")
            if not content:
                content = "[文件] " + record.get("file_name", "未命名")
        elif not content and message_kind not in ("sticker",):
            return

        if receiver_type == "user":
            if not ImFriendRepository.is_friend(self.user["id"], receiver_id):
                self.write_message(json.dumps({
                    "type": "error", "msg": "对方不是您的好友",
                }, ensure_ascii=False))
                return
        elif receiver_type == "group":
            if not ImGroupRepository.is_member(receiver_id, self.user["id"]):
                self.write_message(json.dumps({
                    "type": "error", "msg": "您不是群成员",
                }, ensure_ascii=False))
                return
            if not ImGroupRepository.is_active(receiver_id):
                self.write_message(json.dumps({
                    "type": "error", "msg": "该群已封禁或已解散",
                }, ensure_ascii=False))
                return

        saved = ImMessageRepository.add(
            self.user["id"], receiver_type, receiver_id,
            content, message_kind, file_path, file_id,
        )
        payload = _message_payload(saved)

        if receiver_type == "user":
            broadcast_user(receiver_id, payload)
            broadcast_user(self.user["id"], payload)
        else:
            broadcast_group(receiver_id, payload)

        employee_calls = data.get("employee_calls")
        if employee_calls is None:
            mentions = parse_employee_mentions(content)
            for item in mentions:
                self._reply_employee(item["employee"], item["param"],
                                     receiver_type, receiver_id)
        elif employee_calls:
            for call in employee_calls:
                alias = call.get("alias", "")
                param = call.get("param", "")
                emp = DigitalEmployeeRepository.get_by_alias(alias)
                if emp:
                    self._reply_employee(emp, param, receiver_type, receiver_id)

    def _reply_employee(self, employee, param, receiver_type, receiver_id):
        reply_text = call_employee_reply(
            employee, param, self.user["id"], receiver_type, receiver_id
        )
        bot_msg = ImMessageRepository.add(
            0, receiver_type, receiver_id, reply_text,
            msg_type="employee_call", employee_id=employee["id"],
        )
        bot_msg["sender_name"] = employee.get("name", "数字员工")
        bot_msg["sender_id"] = 0
        payload = _message_payload(bot_msg)
        if receiver_type == "user":
            broadcast_user(self.user["id"], payload)
        else:
            broadcast_group(receiver_id, payload)
