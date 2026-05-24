import json
import os
import re
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


def call_employee_reply(employee, param):
    if employee.get("status") != 1:
        return f"数字员工 {employee.get('name')} 已禁用"
    if employee["category"] == "AI" and employee["agent_type"] == "chat":
        model = ModelEngineRepository.get_default()
        if not model:
            return "系统未配置默认模型"
        prompt = employee.get("prompt", "")
        user_content = param or "你好"
        try:
            from openai import OpenAI
            import httpx
            client = OpenAI(
                api_key=model.get("api_key") or "sk-no-key-required",
                base_url=model.get("base_url") or "https://api.openai.com/v1",
                http_client=httpx.Client(timeout=httpx.Timeout(15.0, connect=5.0)),
            )
            resp = client.chat.completions.create(
                model=model.get("model_name") or "gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=model.get("max_tokens", 2048),
                temperature=model.get("temperature", 0.7),
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"AI 调用出错: {str(e)}"
    if employee["category"] == "普通" and employee["agent_type"] == "api":
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
        body = {"code": code, "msg": msg}
        if data is not None:
            body["data"] = data
        if count is not None:
            body["count"] = count
        self.write(body)


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
        ok, msg = ImFriendRepository.send_request(user["id"], friend_id, message)
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


class ImGroupCreateHandler(ImBaseHandler):
    @tornado.web.authenticated
    def post(self):
        user = self._current_user_dict()
        if not user:
            return self.write_json(1, "用户不存在")
        name = (self.get_body_argument("name", "") or "").strip()
        member_ids_raw = self.get_body_argument("member_ids", "[]")
        if not name:
            return self.write_json(1, "群名称不能为空")
        try:
            member_ids = json.loads(member_ids_raw)
            member_ids = [int(x) for x in member_ids if int(x) != user["id"]]
        except Exception:
            member_ids = []
        group_id = ImGroupRepository.create(name, user["id"], member_ids)
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
        members = ImGroupRepository.get_members(group_id)
        return self.write_json(0, "", members)


class ImGroupInviteHandler(ImBaseHandler):
    @tornado.web.authenticated
    def post(self):
        user = self._current_user_dict()
        if not user:
            return self.write_json(1, "用户不存在")
        group_id = int(self.get_body_argument("group_id", 0))
        member_ids_raw = self.get_body_argument("member_ids", "[]")
        try:
            member_ids = [int(x) for x in json.loads(member_ids_raw)]
        except Exception:
            return self.write_json(1, "成员参数错误")
        ok, msg = ImGroupRepository.add_members(group_id, user["id"], member_ids)
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
        return self.write_json(0, "上传成功", {
            "id": record["id"],
            "file_name": record["file_name"],
            "file_size": record["file_size"],
        })


class ImFileDownloadHandler(ImBaseHandler):
    @tornado.web.authenticated
    def get(self):
        file_id = int(self.get_argument("id", 0))
        record = ImFileRepository.get_by_id(file_id)
        if not record:
            self.set_status(404)
            return self.write("文件不存在")
        path = ImFileRepository.get_full_path(record)
        if not os.path.exists(path):
            self.set_status(404)
            return self.write("文件不存在")
        self.set_header(
            "Content-Disposition",
            f'attachment; filename="{record["file_name"]}"',
        )
        with open(path, "rb") as f:
            self.write(f.read())


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

        reply = call_employee_reply(employee, param)
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

        saved = ImMessageRepository.add(
            self.user["id"], receiver_type, receiver_id,
            content, message_kind, file_path, file_id,
        )
        payload = {"type": "message", "data": saved}

        if receiver_type == "user":
            broadcast_user(receiver_id, payload)
            broadcast_user(self.user["id"], payload)
        else:
            broadcast_group(receiver_id, payload)

        employee_calls = data.get("employee_calls")
        if employee_calls is None and receiver_type == "group":
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
        reply_text = call_employee_reply(employee, param)
        bot_msg = ImMessageRepository.add(
            0, receiver_type, receiver_id, reply_text,
            msg_type="employee_call", employee_id=employee["id"],
        )
        bot_msg["sender_name"] = employee.get("name", "数字员工")
        bot_msg["sender_id"] = 0
        payload = {"type": "message", "data": bot_msg}
        if receiver_type == "user":
            broadcast_user(self.user["id"], payload)
        else:
            broadcast_group(receiver_id, payload)
