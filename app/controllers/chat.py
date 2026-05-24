import json
import tornado.web
import urllib.parse
from app.controllers.base import BaseHandler
from app.models.digital_employee import DigitalEmployeeRepository
from app.models.chat_session import ChatSessionRepository
from app.models.chat_message import ChatMessageRepository
from app.models.model_engine import ModelEngineRepository


class ChatBaseHandler(BaseHandler):
    def get_login_url(self):
        return "/auth/login"

    def get_current_user(self):
        username = self.get_secure_cookie("username")
        if not username:
            return None
        return username.decode("utf-8")


class ChatIndexHandler(ChatBaseHandler):
    @tornado.web.authenticated
    def get(self):
        username = self.current_user
        session_id = self.get_argument("session_id", "")
        self.render("chat.html", username=username, session_id=session_id)


class ChatSessionListHandler(ChatBaseHandler):
    @tornado.web.authenticated
    def get(self):
        username = self.current_user
        user = self._get_user(username)
        if not user:
            return self.write({"code": 1, "msg": "用户不存在"})
        sessions, total = ChatSessionRepository.get_by_user(user["id"])
        self.write({"code": 0, "msg": "", "count": total, "data": sessions})

    def _get_user(self, username):
        from app.models.user import UserRepository
        return UserRepository.get_user_by_username(username)


class ChatSessionAddHandler(ChatBaseHandler):
    @tornado.web.authenticated
    def post(self):
        username = self.current_user
        from app.models.user import UserRepository
        user = UserRepository.get_user_by_username(username)
        if not user:
            return self.write({"code": 1, "msg": "用户不存在"})
        title = self.get_body_argument("title", "新对话")
        model_id = int(self.get_body_argument("model_id", 0))
        sid = ChatSessionRepository.create(user["id"], title, model_id)
        session = ChatSessionRepository.get_by_id(sid)
        self.write({"code": 0, "msg": "创建成功", "data": session})


class ChatSessionDeleteHandler(ChatBaseHandler):
    @tornado.web.authenticated
    def post(self):
        session_id = int(self.get_body_argument("id", 0))
        if not session_id:
            return self.write({"code": 1, "msg": "参数错误"})
        ChatSessionRepository.delete(session_id)
        self.write({"code": 0, "msg": "删除成功"})


class ChatHistoryHandler(ChatBaseHandler):
    @tornado.web.authenticated
    def get(self):
        session_id = int(self.get_argument("session_id", 0))
        if not session_id:
            return self.write({"code": 1, "msg": "参数错误"})
        messages = ChatMessageRepository.get_by_session(session_id)
        self.write({"code": 0, "msg": "", "data": messages})


class ChatEmployeeListHandler(ChatBaseHandler):
    @tornado.web.authenticated
    def get(self):
        employees = DigitalEmployeeRepository.get_all()
        self.write({"code": 0, "msg": "", "data": employees})


class ChatModelListHandler(ChatBaseHandler):
    @tornado.web.authenticated
    def get(self):
        models = ModelEngineRepository.get_all_models()
        self.write({"code": 0, "msg": "", "data": models})


class ChatSendHandler(ChatBaseHandler):
    @tornado.web.authenticated
    async def post(self):
        username = self.current_user
        from app.models.user import UserRepository
        user = UserRepository.get_user_by_username(username)
        if not user:
            return self.write({"code": 1, "msg": "用户不存在"})

        session_id = int(self.get_body_argument("session_id", 0))
        content = self.get_body_argument("content", "").strip()
        model_id = int(self.get_body_argument("model_id", 0))

        if not content:
            return self.write({"code": 1, "msg": "消息不能为空"})

        if not session_id:
            session_id = ChatSessionRepository.create(user["id"], content[:20], model_id)
            session = ChatSessionRepository.get_by_id(session_id)
        else:
            session = ChatSessionRepository.get_by_id(session_id)

        if not session:
            return self.write({"code": 1, "msg": "会话不存在"})

        ChatMessageRepository.add(session_id, "user", content)

        employee_alias, employee_param = self._parse_employee_call(content)

        if employee_alias:
            employee = DigitalEmployeeRepository.get_by_alias(employee_alias)
            if not employee or employee.get("status") != 1:
                ChatMessageRepository.add(session_id, "assistant", f"未找到数字员工 {employee_alias} 或该员工已禁用")
                return self._session_response(session_id)
            if employee["category"] == "AI" and employee["agent_type"] == "chat":
                reply = self._call_ai_employee(employee, employee_param, session_id, model_id)
                ChatMessageRepository.add(session_id, "assistant", reply, msg_type="employee_call", employee_id=employee["id"])
                if session.get("title") == "新对话":
                    ChatSessionRepository.update_title(session_id, employee_param[:20] or employee["name"])
                return self._session_response(session_id)
            elif employee["category"] == "普通" and employee["agent_type"] == "api":
                api_result = self._call_api_employee(employee, employee_param)
                ChatMessageRepository.add(session_id, "assistant", api_result, msg_type="employee_call", employee_id=employee["id"])
                if session.get("title") == "新对话":
                    ChatSessionRepository.update_title(session_id, f"@{employee['name']} " + employee_param[:10])
                return self._session_response(session_id)

        sql_result = self._try_sql_query(content)
        if sql_result is not None:
            reply = self._generate_ai_reply_with_context(content, sql_result)
            ChatMessageRepository.add(session_id, "assistant", reply)
            if session.get("title") == "新对话":
                ChatSessionRepository.update_title(session_id, content[:20])
            return self._session_response(session_id)

        default_model = ModelEngineRepository.get_default()
        if not default_model:
            ChatMessageRepository.add(session_id, "assistant", "系统没有配置默认模型，请联系管理员在后台模型引擎中配置")
            return self._session_response(session_id)

        specified_model = None
        if model_id:
            specified_model = ModelEngineRepository.get_model_by_id(model_id)
        active_model = specified_model or default_model

        ChatMessageRepository.add(session_id, "assistant", self._call_standard_ai(active_model, content, session_id))
        if session.get("title") == "新对话":
            ChatSessionRepository.update_title(session_id, content[:20])

        return self._session_response(session_id)

    def _session_response(self, session_id):
        session = ChatSessionRepository.get_by_id(session_id)
        messages = ChatMessageRepository.get_by_session(session_id)
        self.write({"code": 0, "msg": "", "data": {"session": session, "messages": messages}})

    def _parse_employee_call(self, content):
        import re
        m = re.match(r'^@(\S+)[：:\s]*(.*)', content, re.S)
        if m:
            alias = "@" + m.group(1)
            param = m.group(2).strip()
            return alias, param
        m2 = re.match(r'^@(\S+)$', content.strip())
        if m2:
            return "@" + m2.group(1), ""
        return None, None

    @staticmethod
    def _format_api_result(employee, resp_json):
        try:
            name = employee.get("name", "")
            data = resp_json.get("data", {})
            if name == "音乐" or employee.get("api_service_id", 0) == 1:
                song = data.get("song", "")
                singer = data.get("singer", "")
                cover = data.get("cover", "")
                music_url = data.get("Music", "")
                song_id = data.get("id", "")
                card = f"""🎵 **随机音乐推荐**

<div style="display:flex;align-items:center;gap:16px;margin:12px 0;padding:16px;background:linear-gradient(135deg,#667eea,#764ba2);border-radius:12px;color:#fff;">
  <img src="{cover}" style="width:80px;height:80px;border-radius:8px;object-fit:cover;" onerror="this.style.display='none'">
  <div>
    <div style="font-size:18px;font-weight:bold;">{song}</div>
    <div style="font-size:14px;opacity:0.9;">🎤 {singer}</div>
    <div style="margin-top:8px;">
      <a href="{music_url}" target="_blank" style="display:inline-block;padding:6px 16px;background:#fff;color:#667eea;border-radius:20px;text-decoration:none;font-size:13px;font-weight:bold;">▶ 立即收听</a>
    </div>
  </div>
</div>

> 🆔 歌曲ID: {song_id}"""
                return card

            if name == "天气" or "temp" in data or "weather" in data:
                city = data.get("city", data.get("cityEnglish", ""))
                weather = data.get("weather", "")
                temp = data.get("temp", "")
                tempn = data.get("tempn", "")
                wind = data.get("wind", "")
                cur = data.get("current", {})
                humidity = cur.get("humidity", "")
                air = cur.get("air", "")
                time = cur.get("time", data.get("time", ""))

                weather_icons = {"晴": "☀️", "多云": "⛅", "阴": "☁️", "雨": "🌧️", "雪": "❄️", "雾": "🌫️", "风": "🌬️"}
                icon = "🌡️"
                for kw, emoji in weather_icons.items():
                    if kw in weather:
                        icon = emoji
                        break

                card = f"""🌤️ **{city} 天气预报**

<div style="display:flex;align-items:center;gap:20px;margin:12px 0;padding:20px;background:linear-gradient(135deg,#43e97b,#38f9d7);border-radius:12px;color:#333;">
  <div style="font-size:48px;">{icon}</div>
  <div>
    <div style="font-size:32px;font-weight:bold;">{temp}°C</div>
    <div style="font-size:16px;">{weather}</div>
  </div>
  <div style="font-size:13px;line-height:1.8;">
    最低: {tempn}°C<br>
    风力: {wind}<br>
    湿度: {humidity}<br>
    空气质量: {air}
  </div>
</div>

> 📅 {time}"""
                return card
        except Exception:
            pass
        formatted = json.dumps(resp_json, ensure_ascii=False, indent=2)
        return f"🌐 **{employee.get('name','')}** 返回数据：\n\n```json\n{formatted}\n```"

    def _call_api_employee(self, employee, param):
        import requests
        try:
            api_id = employee.get("api_service_id", 0)
            if not api_id:
                return f"❌ 数字员工 {employee['name']} 未关联 API 服务"
            from app.models.api_service import ApiServiceRepository
            api = ApiServiceRepository.get_by_id(api_id)
            if not api:
                return f"❌ 数字员工 {employee['name']} 关联的 API 服务不存在"

            url = api["url"]
            if param and "{city}" in url:
                url = url.replace("{city}", urllib.parse.quote(param))
            if param and "city=" in url:
                separator = "&" if "?" in url else "?"
                url = f"{url}{separator}city={urllib.parse.quote(param)}"

            safe_headers = {"accept-encoding": "gzip, deflate", "user-agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=safe_headers, timeout=10, verify=False)
            if resp.status_code == 200:
                data = resp.json()
                return ChatSendHandler._format_api_result(employee, data)
            else:
                return f"❌ API 请求失败 (HTTP {resp.status_code})"
        except Exception as e:
            return f"❌ API 调用出错: {str(e)}"

    def _call_ai_employee(self, employee, param, session_id, model_id=0):
        specified_model = None
        if model_id:
            specified_model = ModelEngineRepository.get_model_by_id(model_id)
        active_model = specified_model or ModelEngineRepository.get_default()
        if not active_model:
            return "系统没有配置可用模型，请在后台模型引擎中配置"
        if not param:
            return f"你好！我是**{employee['name']}**，请问有什么可以帮助你的？"

        prompt = employee.get("prompt", "")
        messages = [{"role": "system", "content": prompt}, {"role": "user", "content": param}]
        history = ChatMessageRepository.get_by_session(session_id)
        for msg in history[-10:]:
            if msg["role"] != "system":
                messages.insert(1, {"role": msg["role"], "content": msg["content"]})

        try:
            from openai import OpenAI
            import httpx
            client = OpenAI(
                api_key=active_model.get("api_key") or "sk-no-key-required",
                base_url=active_model.get("base_url") or "https://api.openai.com/v1",
                http_client=httpx.Client(timeout=httpx.Timeout(15.0, connect=5.0))
            )
            resp = client.chat.completions.create(
                model=active_model.get("model_name") or "gpt-3.5-turbo",
                messages=messages,
                max_tokens=active_model.get("max_tokens", 2048),
                temperature=active_model.get("temperature", 0.7)
            )
            reply = resp.choices[0].message.content
            self._update_token_stats(active_model, resp)
            return reply
        except Exception as e:
            err_str = str(e).lower()
            if "timeout" in err_str or "timed out" in err_str:
                return f"⚠️ **{active_model['name']}** 模型请求超时。请在后台模型引擎中检查该模型的 `base_url` 和 `api_key` 配置是否正确，或切换为可正常访问的模型。"
            if "connection" in err_str or "connect" in err_str or "refused" in err_str:
                return f"⚠️ **{active_model['name']}** 模型连接失败。请检查 `base_url` 是否正确，该地址是否可正常访问。"
            if "401" in err_str or "unauthorized" in err_str or "auth" in err_str:
                return f"⚠️ **{active_model['name']}** 模型鉴权失败。请检查 `api_key` 是否正确配置。"
            return f"❌ AI 调用出错: {str(e)}"

    def _update_token_stats(self, model, resp):
        try:
            from app.models.db import get_connection
            usage = getattr(resp, 'usage', None)
            if usage:
                tokens = usage.total_tokens if hasattr(usage, 'total_tokens') else (usage.prompt_tokens + usage.completion_tokens if hasattr(usage, 'prompt_tokens') else 0)
                with get_connection() as conn:
                    conn.execute("UPDATE model_engines SET total_tokens = total_tokens + ?, request_count = request_count + 1 WHERE id = ?",
                                 (tokens, model["id"]))
                    conn.commit()
        except Exception:
            pass

    def _try_sql_query(self, content):
        sql_keywords = ["数据", "采集", "最新", "多少条", "统计", "数据库", "watch", "列表", "查询"]
        if not any(kw in content for kw in sql_keywords):
            return None
        try:
            from app.models.db import get_connection
            with get_connection() as conn:
                if "最新" in content:
                    rows = conn.execute("SELECT * FROM watch_data ORDER BY id DESC LIMIT 5").fetchall()
                elif "多少条" in content or "统计" in content:
                    count = conn.execute("SELECT COUNT(*) FROM watch_data").fetchone()[0]
                    return f"当前数据仓库中共有 **{count}** 条采集数据。"
                elif "列表" in content:
                    rows = conn.execute("SELECT id, title, keyword, create_at FROM watch_data ORDER BY id DESC LIMIT 10").fetchall()
                else:
                    rows = conn.execute("SELECT * FROM watch_data ORDER BY id DESC LIMIT 5").fetchall()
                if rows:
                    result = "📊 **数据查询结果：**\n\n"
                    for r in rows:
                        d = dict(r)
                        result += f"- **{d.get('title','无标题')}** (来源: {d.get('keyword','未知')})\n  [{d.get('url','')}]({d.get('url','')})\n\n"
                    return result
                return "📭 数据仓库中暂无数据，请先通过瞭望管理进行数据采集。"
        except Exception:
            return None

    def _generate_ai_reply_with_context(self, content, sql_result):
        return f"{sql_result}"

    def _call_standard_ai(self, model, content, session_id):
        messages = [{"role": "user", "content": content}]
        history = ChatMessageRepository.get_by_session(session_id)
        for msg in history[-10:]:
            if msg["role"] != "system":
                messages.insert(0, {"role": msg["role"], "content": msg["content"]})

        try:
            from openai import OpenAI
            import httpx
            client = OpenAI(
                api_key=model.get("api_key") or "sk-no-key-required",
                base_url=model.get("base_url") or "https://api.openai.com/v1",
                http_client=httpx.Client(timeout=httpx.Timeout(15.0, connect=5.0))
            )
            resp = client.chat.completions.create(
                model=model.get("model_name") or "gpt-3.5-turbo",
                messages=messages,
                max_tokens=model.get("max_tokens", 2048),
                temperature=model.get("temperature", 0.7)
            )
            reply = resp.choices[0].message.content
            self._update_token_stats(model, resp)
            return reply
        except Exception as e:
            err_str = str(e).lower()
            if "timeout" in err_str or "timed out" in err_str:
                return f"⚠️ **{model['name']}** 模型请求超时。请在后台模型引擎中检查该模型的 `base_url` 和 `api_key` 配置是否正确。"
            if "connection" in err_str or "connect" in err_str or "refused" in err_str:
                return f"⚠️ **{model['name']}** 模型连接失败。请检查 `base_url` 是否正确。"
            if "401" in err_str or "unauthorized" in err_str or "auth" in err_str:
                return f"⚠️ **{model['name']}** 模型鉴权失败。请检查 `api_key` 是否正确配置。"
            return f"❌ AI 对话出错: {str(e)}"


class ChatStreamHandler(ChatBaseHandler):
    @tornado.web.authenticated
    async def get(self):
        username = self.current_user
        from app.models.user import UserRepository
        user = UserRepository.get_user_by_username(username)
        if not user:
            self.set_header("Content-Type", "text/event-stream; charset=utf-8")
            self.write("data: {\"error\": \"用户不存在\"}\n\n")
            self.finish()
            return

        session_id = int(self.get_argument("session_id", 0))
        content = self.get_argument("content", "").strip()
        model_id = int(self.get_argument("model_id", 0))

        if not content or not session_id:
            self.set_header("Content-Type", "text/event-stream; charset=utf-8")
            self.write("data: {\"error\": \"参数错误\"}\n\n")
            self.finish()
            return

        employee_alias, employee_param = self._parse_employee_call(content)
        if employee_alias:
            employee = DigitalEmployeeRepository.get_by_alias(employee_alias)
            if employee and employee.get("status") != 1:
                self.set_header("Content-Type", "text/event-stream; charset=utf-8")
                self.write(f"data: {json.dumps({'content': f'数字员工 {employee_alias} 已禁用', 'done': True})}\n\n")
                self.finish()
                return
            if employee:
                if employee["category"] == "AI" and employee["agent_type"] == "chat":
                    specified_model = None
                    if model_id:
                        specified_model = ModelEngineRepository.get_model_by_id(model_id)
                    active_model = specified_model or ModelEngineRepository.get_default()
                    if not active_model:
                        self.set_header("Content-Type", "text/event-stream; charset=utf-8")
                        self.write(f"data: {json.dumps({'content': '系统没有配置可用模型，请在后台模型引擎中配置', 'done': True})}\n\n")
                        self.finish()
                        return
                    prompt = employee.get("prompt", "")
                    ai_messages = [{"role": "system", "content": prompt}, {"role": "user", "content": employee_param or "你好"}]
                    self._do_sse_stream(session_id, active_model, ai_messages)
                    return
                else:
                    api_result = self._call_api_employee(employee, employee_param)
                    ChatMessageRepository.add(session_id, "assistant", api_result, msg_type="employee_call", employee_id=employee["id"])
                    self.set_header("Content-Type", "text/event-stream; charset=utf-8")
                    self.write(f"data: {json.dumps({'content': api_result, 'done': True})}\n\n")
                    self.finish()
                    return

        specified_model = None
        if model_id:
            specified_model = ModelEngineRepository.get_model_by_id(model_id)
        active_model = specified_model or ModelEngineRepository.get_default()
        if not active_model:
            self.set_header("Content-Type", "text/event-stream; charset=utf-8")
            self.write(f"data: {json.dumps({'content': '系统没有配置可用模型，请在后台模型引擎中配置', 'done': True})}\n\n")
            self.finish()
            return

        sql_result = self._try_sql_query(content)
        if sql_result is not None:
            ChatMessageRepository.add(session_id, "assistant", sql_result)
            self.set_header("Content-Type", "text/event-stream; charset=utf-8")
            self.write(f"data: {json.dumps({'content': sql_result, 'done': True})}\n\n")
            self.finish()
            return

        messages = [{"role": "user", "content": content}]
        history = ChatMessageRepository.get_by_session(session_id)
        for msg in history[-10:]:
            if msg["role"] == "user":
                messages.insert(0, {"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                messages.insert(0, {"role": "assistant", "content": msg["content"]})

        self._do_sse_stream(session_id, active_model, messages)

    def _do_sse_stream(self, session_id, model, messages):
        self.set_header("Content-Type", "text/event-stream; charset=utf-8")
        self.set_header("Cache-Control", "no-cache")
        self.set_header("Connection", "keep-alive")
        try:
            from openai import OpenAI
            import httpx
            client = OpenAI(
                api_key=model.get("api_key") or "sk-no-key-required",
                base_url=model.get("base_url") or "https://api.openai.com/v1",
                http_client=httpx.Client(timeout=httpx.Timeout(30.0, connect=5.0))
            )
            stream = client.chat.completions.create(
                model=model.get("model_name") or "gpt-3.5-turbo",
                messages=messages,
                max_tokens=model.get("max_tokens", 2048),
                temperature=model.get("temperature", 0.7),
                stream=True
            )
            full_reply = ""
            for chunk in stream:
                delta = chunk.choices[0].delta if hasattr(chunk.choices[0], 'delta') else None
                if delta and hasattr(delta, 'content') and delta.content:
                    full_reply += delta.content
                    self.write(f"data: {json.dumps({'content': delta.content, 'done': False})}\n\n")
                    self.flush()
            ChatMessageRepository.add(session_id, "assistant", full_reply)
            self.write(f"data: {json.dumps({'content': '', 'done': True})}\n\n")
            self.finish()
        except Exception as e:
            err_str = str(e).lower()
            if "timeout" in err_str or "timed out" in err_str:
                error_msg = f"⚠️ **{model['name']}** 模型请求超时。请在后台引擎中检查配置。"
            elif "connection" in err_str or "connect" in err_str or "refused" in err_str:
                error_msg = f"⚠️ **{model['name']}** 模型连接失败。请检查 `base_url` 是否正确。"
            elif "401" in err_str or "unauthorized" in err_str or "auth" in err_str:
                error_msg = f"⚠️ **{model['name']}** 模型鉴权失败。请检查 `api_key`。"
            else:
                error_msg = f"❌ AI 对话出错: {str(e)}"
            ChatMessageRepository.add(session_id, "assistant", error_msg)
            self.write(f"data: {json.dumps({'error': error_msg})}\n\n")
            self.finish()

    def _parse_employee_call(self, content):
        import re
        m = re.match(r'^@(\S+)[：:\s]*(.*)', content, re.S)
        if m:
            return "@" + m.group(1), m.group(2).strip()
        m2 = re.match(r'^@(\S+)$', content.strip())
        if m2:
            return "@" + m2.group(1), ""
        return None, None

    def _call_api_employee(self, employee, param):
        import requests
        try:
            api_id = employee.get("api_service_id", 0)
            if not api_id:
                return f"❌ 数字员工 {employee['name']} 未关联 API 服务"
            from app.models.api_service import ApiServiceRepository
            api = ApiServiceRepository.get_by_id(api_id)
            if not api:
                return f"❌ 数字员工 {employee['name']} 关联的 API 服务不存在"
            url = api["url"]
            if param and "city=" in url:
                sep = "&" if "?" in url else "?"
                url = f"{url}{sep}city={urllib.parse.quote(param)}"
            safe_headers = {"accept-encoding": "gzip, deflate", "user-agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=safe_headers, timeout=10, verify=False)
            if resp.status_code == 200:
                data = resp.json()
                return ChatSendHandler._format_api_result(employee, data)
            else:
                return f"❌ API 请求失败 (HTTP {resp.status_code})"
        except Exception as e:
            return f"❌ API 调用出错: {str(e)}"

    def _try_sql_query(self, content):
        sql_keywords = ["数据", "采集", "最新", "多少条", "统计", "数据库", "watch", "列表", "查询"]
        if not any(kw in content for kw in sql_keywords):
            return None
        try:
            from app.models.db import get_connection
            with get_connection() as conn:
                if "最新" in content:
                    rows = conn.execute("SELECT * FROM watch_data ORDER BY id DESC LIMIT 5").fetchall()
                elif "多少条" in content or "统计" in content:
                    count = conn.execute("SELECT COUNT(*) FROM watch_data").fetchone()[0]
                    return f"📊 当前数据仓库中共有 **{count}** 条采集数据。"
                elif "列表" in content:
                    rows = conn.execute("SELECT id, title, keyword, create_at FROM watch_data ORDER BY id DESC LIMIT 10").fetchall()
                else:
                    rows = conn.execute("SELECT * FROM watch_data ORDER BY id DESC LIMIT 5").fetchall()
                if rows:
                    result = "📊 **数据查询结果：**\n\n"
                    for r in rows:
                        d = dict(r)
                        result += f"- **{d.get('title','无标题')}** (关键词: {d.get('keyword','未知')})\n  [查看链接]({d.get('url','')})\n\n"
                    return result
                return "📭 数据仓库中暂无数据。"
        except Exception:
            return None
