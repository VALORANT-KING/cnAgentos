import json
import tornado.web
from app.controllers.base import BaseHandler
from app.models.user import UserRepository
from app.models.module import ModuleRepository
from app.models.role import RoleRepository
from app.models.model_engine import ModelEngineRepository
from app.models.watch import WatchRepository
from app.models.api_service import ApiServiceRepository
from app.models.digital_employee import DigitalEmployeeRepository
from app.models.auto_task import AutoTaskRepository
from app.models.db_config import DbConfigRepository
from app.scheduler import start_task, stop_task, execute_auto_task
import requests
import urllib3
from bs4 import BeautifulSoup
import re

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class AdminBaseHandler(BaseHandler):
    def get_login_url(self):
        return "/admin/login"

    def get_current_user(self):
        username = self.get_secure_cookie("admin_username")
        if not username:
            return None
        user = UserRepository.get_user_by_username(username.decode('utf-8'))
        if not user or user.get("role") != "admin":
            return None
        return user

class AdminLoginHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("admin_login.html", error=None)

    def post(self):
        username = (self.get_body_argument("username", "") or "").strip()
        password = self.get_body_argument("password", "")

        if not username or not password:
            return self.render("admin_login.html", error="用户名或密码不能为空")

        user = UserRepository.get_user_by_username(username)
        if not user or user.get("role") != "admin":
            return self.render("admin_login.html", error="无管理员权限或账号不存在")

        if int(user.get("status") or 0) != 1:
            return self.render("admin_login.html", error="账号已被禁用，请联系系统管理员")

        if not UserRepository.verify_user(username, password):
            return self.render("admin_login.html", error="用户名或密码错误")

        self.set_secure_cookie("admin_username", username)
        self.redirect("/admin")

class AdminLogoutHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        self.clear_cookie("admin_username")
        self.redirect("/admin/login")

class AdminIndexHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        # 确保 current_user 存在
        username = self.current_user["username"] if self.current_user else "未知用户"
        self.render("admin_index.html", username=username)

class AdminHomeHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_home.html")


class AdminHomeStatsHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        from app.models.db import get_connection
        try:
            with get_connection() as conn:
                total_users = conn.execute("SELECT COUNT(*) AS cnt FROM users").fetchone()["cnt"]
                total_employees = conn.execute("SELECT COUNT(*) AS cnt FROM digital_employees").fetchone()["cnt"]
                total_sources = conn.execute("SELECT COUNT(*) AS cnt FROM watch_sources").fetchone()["cnt"]
                total_tasks = conn.execute("SELECT COUNT(*) AS cnt FROM auto_tasks").fetchone()["cnt"]
            self.write({
                "code": 0,
                "data": {
                    "total_users": total_users,
                    "total_employees": total_employees,
                    "total_sources": total_sources,
                    "total_tasks": total_tasks,
                },
            })
        except Exception as e:
            self.write({"code": 1, "msg": str(e)})


class AdminUserManageHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        username = self.current_user["username"] if self.current_user else "未知用户"
        self.render("admin_user_manage.html", username=username)

class AdminUserListHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1))
        limit = int(self.get_argument("limit", 20))
        users, total = UserRepository.get_all_users(page, limit)

        result_data = []
        for u in users:
            result_data.append({
                "id": u["id"],
                "username": u["username"],
                "role": u["role"],
                "status": u["status"],
                "create_at": u["create_at"]
            })

        self.write({
            "code": 0,
            "msg": "",
            "count": total,
            "data": result_data
        })

class AdminUserAddHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        username = (self.get_body_argument("username", "") or "").strip()
        password = self.get_body_argument("password", "")
        role = self.get_body_argument("role", "user")
        status = int(self.get_body_argument("status", 1))

        if not username or not password:
            return self.write({"code": 1, "msg": "用户名和密码不能为空"})

        if len(password) < 6:
            return self.write({"code": 1, "msg": "密码长度不能少于6位"})

        success = UserRepository.create_user(username, password, role)
        if success:
            if status == 0:
                user = UserRepository.get_user_by_username(username)
                if user:
                    UserRepository.update_user(user["id"], status=0)
            return self.write({"code": 0, "msg": "添加成功"})
        else:
            return self.write({"code": 1, "msg": "用户名已存在"})

class AdminUserUpdateHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        user_id = int(self.get_body_argument("id", 0))
        password = self.get_body_argument("password", "")
        role = self.get_body_argument("role", None)
        status = self.get_body_argument("status", None)

        if not user_id:
            return self.write({"code": 1, "msg": "用户ID不能为空"})

        user = UserRepository.get_user_by_id(user_id)
        if not user:
            return self.write({"code": 1, "msg": "用户不存在"})

        if user["username"] == "admin" and user["id"] == 1:
            if password:
                if len(password) < 6:
                    return self.write({"code": 1, "msg": "密码长度不能少于6位"})
                UserRepository.update_user(user_id, password=password)
                return self.write({"code": 0, "msg": "密码修改成功"})
            return self.write({"code": 1, "msg": "超级管理员仅支持修改密码"})

        if password and len(password) < 6:
            return self.write({"code": 1, "msg": "密码长度不能少于6位"})

        update_status = int(status) if status is not None else None
        success = UserRepository.update_user(
            user_id,
            password=password if password else None,
            role=role,
            status=update_status
        )

        if success:
            return self.write({"code": 0, "msg": "修改成功"})
        else:
            return self.write({"code": 1, "msg": "修改失败"})

class AdminUserDeleteHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        user_ids_str = self.get_body_argument("ids", "")
        if not user_ids_str:
            return self.write({"code": 1, "msg": "请选择要删除的用户"})

        user_ids = [int(x) for x in user_ids_str.split(",") if x.strip().isdigit()]
        if not user_ids:
            return self.write({"code": 1, "msg": "用户ID格式错误"})

        if 1 in user_ids:
            return self.write({"code": 1, "msg": "超级管理员 admin 不能删除"})

        current_user = self.current_user
        if current_user and current_user["id"] in user_ids:
            return self.write({"code": 1, "msg": "不能删除当前登录账号"})

        success = UserRepository.delete_users_batch(user_ids)
        if success:
            return self.write({"code": 0, "msg": f"成功删除{len(user_ids)}个用户"})
        else:
            return self.write({"code": 1, "msg": "删除失败"})

class AdminMenuHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        tree = ModuleRepository.get_module_tree()
        self.write({"code": 0, "data": tree})

class AdminModuleManageHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_module_manage.html")

class AdminModuleListHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        modules = ModuleRepository.get_all_modules()
        parents = ModuleRepository.get_parent_modules()
        self.write({"code": 0, "data": modules, "parents": parents})

class AdminModuleAddHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        name = self.get_body_argument("name", "").strip()
        icon = self.get_body_argument("icon", "")
        url = self.get_body_argument("url", "")
        parent_id = int(self.get_body_argument("parent_id", 0))
        sort_order = int(self.get_body_argument("sort_order", 0))
        if not name:
            return self.write({"code": 1, "msg": "模块名称不能为空"})
        ok = ModuleRepository.add_module(name, icon, url, parent_id, sort_order)
        return self.write({"code": 0 if ok else 1, "msg": "添加成功" if ok else "添加失败"})

class AdminModuleUpdateHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        module_id = int(self.get_body_argument("id", 0))
        name = self.get_body_argument("name", "").strip()
        icon = self.get_body_argument("icon", "")
        url = self.get_body_argument("url", "")
        parent_id = int(self.get_body_argument("parent_id", 0))
        sort_order = int(self.get_body_argument("sort_order", 0))
        status = int(self.get_body_argument("status", 1))
        if not name:
            return self.write({"code": 1, "msg": "模块名称不能为空"})
        ok = ModuleRepository.update_module(module_id, name, icon, url, parent_id, sort_order, status)
        return self.write({"code": 0 if ok else 1, "msg": "修改成功" if ok else "修改失败"})

class AdminModuleDeleteHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        module_id = int(self.get_body_argument("id", 0))
        ok = ModuleRepository.delete_module(module_id)
        return self.write({"code": 0 if ok else 1, "msg": "删除成功" if ok else "删除失败"})

class AdminRoleManageHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_role_manage.html")

class AdminRoleListHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        roles = RoleRepository.get_all_roles()
        self.write({"code": 0, "data": roles})

class AdminRoleAddHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        name = self.get_body_argument("name", "").strip()
        description = self.get_body_argument("description", "")
        if not name:
            return self.write({"code": 1, "msg": "角色名称不能为空"})
        ok = RoleRepository.add_role(name, description)
        return self.write({"code": 0 if ok else 1, "msg": "添加成功" if ok else "角色名重复"})

class AdminRoleUpdateHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        role_id = int(self.get_body_argument("id", 0))
        name = self.get_body_argument("name", "").strip()
        description = self.get_body_argument("description", "")
        status = int(self.get_body_argument("status", 1))
        ok = RoleRepository.update_role(role_id, name, description, status)
        return self.write({"code": 0 if ok else 1, "msg": "修改成功" if ok else "系统角色不能修改"})

class AdminRoleDeleteHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        role_id = int(self.get_body_argument("id", 0))
        ok = RoleRepository.delete_role(role_id)
        return self.write({"code": 0 if ok else 1, "msg": "删除成功" if ok else "系统角色不能删除"})

class AdminPermissionManageHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_permission_manage.html")

class AdminPermissionLoadHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        role_id = int(self.get_argument("role_id", 0))
        modules = ModuleRepository.get_all_modules()
        permissions = RoleRepository.get_role_permissions(role_id) if role_id else []
        tree = []
        parent_map = {}
        for m in modules:
            m["checked"] = m["id"] in permissions
            if m["parent_id"] == 0:
                tree.append(m)
                parent_map[m["id"]] = m
                m["children"] = []
            else:
                if m["parent_id"] in parent_map:
                    parent_map[m["parent_id"]]["children"].append(m)
        self.write({"code": 0, "data": tree})

class AdminPermissionSaveHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        role_id = int(self.get_body_argument("role_id", 0))
        module_ids = self.get_body_argument("module_ids", "")
        if not role_id:
            return self.write({"code": 1, "msg": "请选择角色"})
        ids = [int(x) for x in module_ids.split(",") if x.strip().isdigit()]
        ok = RoleRepository.save_role_permissions(role_id, ids)
        return self.write({"code": 0 if ok else 1, "msg": "保存成功" if ok else "保存失败"})

class AdminRoleSelectHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        roles = RoleRepository.get_roles_for_select()
        self.write({"code": 0, "data": roles})

class AdminModelManageHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_model_manage.html")

class AdminModelListHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1))
        limit = int(self.get_argument("limit", 6))
        engines, total = ModelEngineRepository.get_all_engines(page, limit)
        self.write({"code": 0, "msg": "", "count": total, "data": engines})

class AdminModelAddHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        name = self.get_body_argument("name", "").strip()
        provider = self.get_body_argument("provider", "openai")
        base_url = self.get_body_argument("base_url", "").strip()
        api_key = self.get_body_argument("api_key", "").strip()
        model_name = self.get_body_argument("model_name", "").strip()
        engine_type = self.get_body_argument("type", "remote")
        max_tokens = int(self.get_body_argument("max_tokens", 2048))
        temperature = float(self.get_body_argument("temperature", 0.7))
        description = self.get_body_argument("description", "").strip()

        if not name or not base_url or not model_name:
            return self.write({"code": 1, "msg": "模型名称、API地址和模型标识不能为空"})

        ok = ModelEngineRepository.add_engine(
            name, provider, base_url, api_key, model_name,
            engine_type, max_tokens, temperature, description
        )
        return self.write({"code": 0 if ok else 1, "msg": "添加成功" if ok else "添加失败"})

class AdminModelUpdateHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        engine_id = int(self.get_body_argument("id", 0))
        name = self.get_body_argument("name", "").strip()
        provider = self.get_body_argument("provider", "openai")
        base_url = self.get_body_argument("base_url", "").strip()
        api_key = self.get_body_argument("api_key", "").strip()
        model_name = self.get_body_argument("model_name", "").strip()
        engine_type = self.get_body_argument("type", "remote")
        max_tokens = int(self.get_body_argument("max_tokens", 2048))
        temperature = float(self.get_body_argument("temperature", 0.7))
        description = self.get_body_argument("description", "").strip()
        status = int(self.get_body_argument("status", 1))

        if not engine_id or not name:
            return self.write({"code": 1, "msg": "参数不能为空"})

        ok = ModelEngineRepository.update_engine(
            engine_id, name, provider, base_url, api_key, model_name,
            engine_type, max_tokens, temperature, description, status
        )
        return self.write({"code": 0 if ok else 1, "msg": "修改成功" if ok else "修改失败"})

class AdminModelDeleteHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        engine_id = int(self.get_body_argument("id", 0))
        if not engine_id:
            return self.write({"code": 1, "msg": "请选择要删除的模型"})
        ok = ModelEngineRepository.delete_engine(engine_id)
        return self.write({"code": 0 if ok else 1, "msg": "删除成功" if ok else "默认模型不能删除，请先取消默认"})

class AdminModelSetDefaultHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        engine_id = int(self.get_body_argument("id", 0))
        if not engine_id:
            return self.write({"code": 1, "msg": "请选择模型"})
        ok = ModelEngineRepository.set_default_engine(engine_id)
        return self.write({"code": 0 if ok else 1, "msg": "设置成功" if ok else "设置失败"})

class AdminModelChatHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        engine_id = int(self.get_body_argument("id", 0))
        message = self.get_body_argument("message", "").strip()
        if not engine_id or not message:
            return self.write({"code": 1, "msg": "参数不能为空"})

        engine = ModelEngineRepository.get_engine_by_id(engine_id)
        if not engine:
            return self.write({"code": 1, "msg": "模型不存在"})

        try:
            from openai import OpenAI
            client = OpenAI(api_key=engine["api_key"] or "sk-placeholder", base_url=engine["base_url"])
            response = client.chat.completions.create(
                model=engine["model_name"],
                messages=[{"role": "user", "content": message}],
                max_tokens=engine["max_tokens"],
                temperature=engine["temperature"]
            )
            reply = response.choices[0].message.content
            usage = response.usage
            if usage:
                ModelEngineRepository.add_token_usage(engine_id, usage.total_tokens)
            return self.write({"code": 0, "data": {"reply": reply, "usage": {"total": usage.total_tokens if usage else 0}}})
        except ImportError:
            return self.write({"code": 1, "msg": "OpenAI SDK 未安装，请在部署环境执行: pip install openai"})
        except Exception as e:
            return self.write({"code": 1, "msg": f"调用失败: {str(e)}"})

class AdminModelChatStreamHandler(AdminBaseHandler):
    @tornado.web.authenticated
    async def post(self):
        engine_id = int(self.get_body_argument("id", 0))
        message = self.get_body_argument("message", "").strip()
        if not engine_id or not message:
            self.set_status(400)
            return self.finish()

        engine = ModelEngineRepository.get_engine_by_id(engine_id)
        if not engine:
            self.set_status(404)
            return self.finish()

        self.set_header("Content-Type", "text/event-stream")
        self.set_header("Cache-Control", "no-cache")
        self.set_header("Connection", "keep-alive")
        self.set_header("X-Accel-Buffering", "no")

        try:
            from openai import OpenAI
            client = OpenAI(api_key=engine["api_key"] or "sk-placeholder", base_url=engine["base_url"])
            stream = client.chat.completions.create(
                model=engine["model_name"],
                messages=[{"role": "user", "content": message}],
                max_tokens=engine["max_tokens"],
                temperature=engine["temperature"],
                stream=True
            )
            total_tokens = 0
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    self.write(f"data: {json.dumps({'content': content})}\n\n")
                    await self.flush()
                if chunk.usage:
                    total_tokens = chunk.usage.total_tokens
            if total_tokens > 0:
                ModelEngineRepository.add_token_usage(engine_id, total_tokens)
            self.write("data: [DONE]\n\n")
            await self.flush()
        except ImportError:
            self.write(f"data: {json.dumps({'error': 'OpenAI SDK 未安装，请在部署环境执行: pip install openai'})}\n\n")
            await self.flush()
        except Exception as e:
            self.write(f"data: {json.dumps({'error': str(e)})}\n\n")
            await self.flush()

# --- 瞭望管理 ---

class AdminWatchSourceHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_watch_source.html")

class AdminWatchSourceListHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        sources = WatchRepository.get_all_sources()
        self.write({"code": 0, "msg": "", "count": len(sources), "data": sources})

class AdminWatchSourceAddHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        name = self.get_body_argument("name", "").strip()
        url_pattern = self.get_body_argument("url_pattern", "").strip()
        headers = self.get_body_argument("headers", "{}").strip()
        
        if not name or not url_pattern:
            return self.write({"code": 1, "msg": "名称和URL模板不能为空"})
        
        try:
            json.loads(headers)
        except:
            return self.write({"code": 1, "msg": "Headers格式不正确，请输入JSON格式"})
            
        WatchRepository.add_source(name, url_pattern, headers)
        self.write({"code": 0, "msg": "添加成功"})

class AdminWatchSourceUpdateHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        source_id = int(self.get_body_argument("id", 0))
        name = self.get_body_argument("name", "").strip()
        url_pattern = self.get_body_argument("url_pattern", "").strip()
        headers = self.get_body_argument("headers", "{}").strip()
        status = int(self.get_body_argument("status", 1))
        
        if not source_id or not name or not url_pattern:
            return self.write({"code": 1, "msg": "参数错误"})
            
        WatchRepository.update_source(source_id, name, url_pattern, headers, status=status)
        self.write({"code": 0, "msg": "更新成功"})

class AdminWatchSourceDeleteHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        source_id = int(self.get_body_argument("id", 0))
        if not source_id:
            return self.write({"code": 1, "msg": "参数错误"})
        WatchRepository.delete_source(source_id)
        self.write({"code": 0, "msg": "删除成功"})

class AdminWatchCollectHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_watch_collect.html")


class AdminWatchCollectSourcesHandler(AdminBaseHandler):
    """采集页专用：返回与瞭望源管理一致的启用源列表。"""

    @tornado.web.authenticated
    def get(self):
        sources = WatchRepository.get_active_sources()
        self.write({"code": 0, "msg": "", "count": len(sources), "data": sources})

class AdminWatchDoCollectHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        try:
            keyword = self.get_body_argument("keyword", "").strip()
            source_ids = self.get_body_arguments("source_ids")
            pages = int(self.get_body_argument("pages", 1))
            
            if not keyword or not source_ids:
                return self.write({"code": 1, "msg": "关键词和采集源不能为空"})
                
            total_parsed = 0
            total_saved = 0
            
            # 使用 Session 维持 Cookie
            session = requests.Session()
            
            for s_id in source_ids:
                source = WatchRepository.get_source_by_id(int(s_id))
                if not source: continue
                
                headers = {}
                if source['headers']:
                    try:
                        headers = json.loads(source['headers'])
                    except: pass
                
                # 更新 session 的 headers，并强制排除 br/zstd 以防解码失败
                safe_headers = headers.copy()
                safe_headers["accept-encoding"] = "gzip, deflate"
                session.headers.update(safe_headers)
                
                collected_items = []
                for p in range(pages):
                    pn = p * 10 # 百度分页步进
                    url = source['url_pattern'].replace("{关键词}", keyword).replace("{分页}", str(pn))
                    
                    try:
                        print(f"DEBUG: Requesting URL via Session: {url}")
                        # 使用会话发送请求，禁用 SSL 验证
                        resp = session.get(url, timeout=15, allow_redirects=True, verify=False)
                        print(f"DEBUG: Response Status: {resp.status_code}, Final URL: {resp.url}")
                        
                        if resp.status_code == 200:
                            # 确定编码
                            encoding = resp.encoding
                            if not encoding or encoding.lower() == 'iso-8859-1':
                                encoding = resp.apparent_encoding
                            
                            # 如果内容中显式指定了 gbk
                            if 'charset=gbk' in resp.text.lower():
                                encoding = 'gbk'
                                
                            html_content = resp.content.decode(encoding, errors='replace')
                            
                            items = self._parse_baidu_news(html_content)
                            collected_items.extend(items)
                            total_parsed += len(items)
                        else:
                            print(f"DEBUG: Failed to collect, status code: {resp.status_code}")
                    except Exception as e:
                        print(f"DEBUG: Request failed: {e}")
                
                if collected_items:
                    saved = WatchRepository.save_collected_data(
                        source["id"], keyword, collected_items
                    )
                    total_saved += saved
                    
            msg = f"采集完成：解析到 {total_parsed} 条数据"
            if total_saved > 0:
                msg += f"，其中 {total_saved} 条为新数据并已入库。"
            elif total_parsed > 0:
                msg += f"，但均为重复数据（已存在于数据库中）。"
            else:
                msg += f"，未能从页面中提取到有效信息，请检查采集源配置或 Cookie 是否过期。"
                
            self.write({"code": 0, "msg": msg, "count": total_saved})
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.write({"code": 1, "msg": f"系统内部错误: {str(e)}"})

    def _parse_baidu_news(self, html):
        items = []
        
        # 方案 1: 尝试解析嵌入的 JSON 数据 (s-data)
        # 这种方式最准确，因为百度将结构化数据直接写在了注释中
        s_data_matches = re.findall(r'<!--s-data:(\{.*?\})-->', html)
        print(f"DEBUG: Found {len(s_data_matches)} s-data matches")
        
        for match in s_data_matches:
            try:
                data = json.loads(match)
                if 'title' in data and 'titleUrl' in data:
                    title = re.sub(r'<.*?>', '', data['title'])
                    items.append({
                        "title": title,
                        "url": data['titleUrl'],
                        "content": data.get('summary', ''),
                        "publish_time": data.get('dispTime', '')
                    })
            except Exception as e:
                print(f"DEBUG: JSON parse error in s-data: {e}")
                continue
                
        # 方案 2: 通用 HTML 解析
        if len(items) < 3:
            print("DEBUG: Using fallback HTML parsing...")
            soup = BeautifulSoup(html, 'html.parser')
            results = soup.select('div[mu], .result-op, .c-container')
            
            for res in results:
                try:
                    title_el = res.select_one('h3 a') or res.select_one('a[href]')
                    if not title_el: continue
                    
                    url = title_el.get('href', '')
                    title = title_el.get_text(strip=True)
                    
                    if not url or 'baidu.com' in url or url.startswith('/') or len(title) < 5:
                        continue
                        
                    if any(item['url'] == url for item in items):
                        continue

                    content = ""
                    content_el = res.select_one('.c-font-normal') or res.select_one('.c-abstract')
                    if content_el:
                        content = content_el.get_text(strip=True)
                    
                    publish_time = ""
                    time_el = res.select_one('.c-color-gray2') or res.select_one('.c-showurl')
                    if time_el:
                        time_text = time_el.get_text(strip=True)
                        time_match = re.search(r'\d+小时前|\d+分钟前|\d+天前|\d{4}年\d+月\d+日', time_text)
                        if time_match:
                            publish_time = time_match.group()

                    items.append({
                        "title": title,
                        "url": url,
                        "content": content,
                        "publish_time": publish_time
                    })
                except:
                    continue

        # 方案 3: 终极正则提取 (针对标题和链接)
        if len(items) < 3:
            print("DEBUG: Using extreme regex extraction...")
            # 匹配 <h3>...href="(http...)"...>(...)</a>...</h3>
            regex_matches = re.findall(r'<h3.*?href="(http.*?)".*?>(.*?)</a>', html, re.S)
            for url, title in regex_matches:
                if 'baidu.com' in url or len(title) < 5: continue
                clean_title = re.sub(r'<.*?>', '', title).strip()
                if not any(item['url'] == url for item in items):
                    items.append({
                        "title": clean_title,
                        "url": url,
                        "content": "",
                        "publish_time": ""
                    })
        
        # 最后的去重
        unique_items = []
        seen_urls = set()
        for item in items:
            if item['url'] not in seen_urls:
                unique_items.append(item)
                seen_urls.add(item['url'])
                
        print(f"DEBUG: Final unique items parsed: {len(unique_items)}")
        return unique_items

class AdminWatchDataHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_watch_data.html")

class AdminWatchDataListHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1))
        limit = int(self.get_argument("limit", 20))
        keyword = self.get_argument("keyword", "").strip()
        
        data, total = WatchRepository.get_all_data(page, limit, keyword)
        self.write({"code": 0, "msg": "", "count": total, "data": data})

class AdminWatchDataDeleteHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        ids_str = self.get_body_argument("ids", "")
        if not ids_str:
            return self.write({"code": 1, "msg": "未选择任何数据"})
        
        ids = [int(i) for i in ids_str.split(',') if i]
        WatchRepository.delete_data(ids)
        self.write({"code": 0, "msg": "删除成功"})


class AdminApiManageHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_api_manage.html")


class AdminApiListHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1))
        limit = int(self.get_argument("limit", 20))
        keyword = self.get_argument("keyword", "").strip()

        data, total = ApiServiceRepository.get_list(page, limit, keyword)
        self.write({"code": 0, "msg": "", "count": total, "data": data})


class AdminApiAddHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        name = self.get_body_argument("name", "").strip()
        url = self.get_body_argument("url", "").strip()
        method = self.get_body_argument("method", "GET").strip()
        resp_format = self.get_body_argument("resp_format", "JSON").strip()
        qps_limit = int(self.get_body_argument("qps_limit", 0))
        token = self.get_body_argument("token", "").strip()
        description = self.get_body_argument("description", "").strip()

        if not name or not url:
            return self.write({"code": 1, "msg": "接口名称和地址不能为空"})

        ApiServiceRepository.add(name, url, method, resp_format, qps_limit, token, description)
        self.write({"code": 0, "msg": "添加成功"})


class AdminApiUpdateHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        api_id = int(self.get_body_argument("id", 0))
        name = self.get_body_argument("name", "").strip()
        url = self.get_body_argument("url", "").strip()
        method = self.get_body_argument("method", "GET").strip()
        resp_format = self.get_body_argument("resp_format", "JSON").strip()
        qps_limit = int(self.get_body_argument("qps_limit", 0))
        token = self.get_body_argument("token", "").strip()
        status = int(self.get_body_argument("status", 1))
        description = self.get_body_argument("description", "").strip()

        if not api_id or not name or not url:
            return self.write({"code": 1, "msg": "参数错误"})

        ApiServiceRepository.update(api_id, name, url, method, resp_format, qps_limit, token, status, description)
        self.write({"code": 0, "msg": "更新成功"})


class AdminApiDeleteHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        api_id = int(self.get_body_argument("id", 0))
        if not api_id:
            return self.write({"code": 1, "msg": "参数错误"})
        ApiServiceRepository.delete(api_id)
        self.write({"code": 0, "msg": "删除成功"})


class AdminEmployeeManageHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_employee_manage.html")


class AdminEmployeeListHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1))
        limit = int(self.get_argument("limit", 20))
        keyword = self.get_argument("keyword", "").strip()

        data, total = DigitalEmployeeRepository.get_list(page, limit, keyword)
        self.write({"code": 0, "msg": "", "count": total, "data": data})


class AdminEmployeeAddHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        name = self.get_body_argument("name", "").strip()
        alias = self.get_body_argument("alias", "").strip()
        category = self.get_body_argument("category", "AI").strip()
        agent_type = self.get_body_argument("agent_type", "chat").strip()
        api_service_id = int(self.get_body_argument("api_service_id", 0))
        prompt = self.get_body_argument("prompt", "").strip()
        icon = self.get_body_argument("icon", "fa-robot").strip()
        description = self.get_body_argument("description", "").strip()
        sort_order = int(self.get_body_argument("sort_order", 0))

        if not name or not alias:
            return self.write({"code": 1, "msg": "名称和别名不能为空"})

        existing = DigitalEmployeeRepository.get_by_alias(alias)
        if existing:
            return self.write({"code": 1, "msg": "别名已存在，请使用其他别名"})

        DigitalEmployeeRepository.add(name, alias, category, agent_type, api_service_id, prompt, icon, description, sort_order)
        self.write({"code": 0, "msg": "添加成功"})


class AdminEmployeeUpdateHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        emp_id = int(self.get_body_argument("id", 0))
        name = self.get_body_argument("name", "").strip()
        alias = self.get_body_argument("alias", "").strip()
        category = self.get_body_argument("category", "AI").strip()
        agent_type = self.get_body_argument("agent_type", "chat").strip()
        api_service_id = int(self.get_body_argument("api_service_id", 0))
        prompt = self.get_body_argument("prompt", "").strip()
        icon = self.get_body_argument("icon", "fa-robot").strip()
        description = self.get_body_argument("description", "").strip()
        sort_order = int(self.get_body_argument("sort_order", 0))
        status = int(self.get_body_argument("status", 1))

        if not emp_id or not name or not alias:
            return self.write({"code": 1, "msg": "参数错误"})

        existing = DigitalEmployeeRepository.get_by_alias(alias)
        if existing and existing["id"] != emp_id:
            return self.write({"code": 1, "msg": "别名已被其他员工使用"})

        DigitalEmployeeRepository.update(emp_id, name, alias, category, agent_type, api_service_id, prompt, icon, description, sort_order, status)
        self.write({"code": 0, "msg": "更新成功"})


class AdminEmployeeDeleteHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        emp_id = int(self.get_body_argument("id", 0))
        if not emp_id:
            return self.write({"code": 1, "msg": "参数错误"})
        DigitalEmployeeRepository.delete(emp_id)
        self.write({"code": 0, "msg": "删除成功"})


# ── 团队任务2：智能聊天后台管理 ──

class AdminImGroupsHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_im_groups.html")


class AdminImGroupsListHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        from app.models.im_group import ImGroupRepository
        page = int(self.get_argument("page", 1))
        limit = int(self.get_argument("limit", 20))
        keyword = self.get_argument("keyword", "").strip()
        data, total = ImGroupRepository.get_all(page, limit, keyword or None)
        self.write({"code": 0, "msg": "", "count": total, "data": data})


class AdminImGroupsDissolveHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        from app.models.im_group import ImGroupRepository
        group_id = int(self.get_body_argument("group_id", 0))
        if not group_id:
            return self.write({"code": 1, "msg": "参数错误"})
        ok, msg = ImGroupRepository.dissolve(group_id)
        if ok:
            from app.controllers.im import broadcast_group
            block_msg = ImGroupRepository.get_block_message(group_id)
            broadcast_group(group_id, {
                "type": "group_status",
                "group_id": group_id,
                "status": 2,
                "message": block_msg or "",
            })
        self.write({"code": 0 if ok else 1, "msg": msg})


class AdminImGroupsBanHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        from app.models.im_group import ImGroupRepository
        group_id = int(self.get_body_argument("group_id", 0))
        status = int(self.get_body_argument("status", 0))
        if not group_id:
            return self.write({"code": 1, "msg": "参数错误"})
        ok, msg = ImGroupRepository.set_status(group_id, status)
        if ok:
            from app.controllers.im import broadcast_group
            block_msg = ImGroupRepository.get_block_message(group_id) if status == 0 else ""
            broadcast_group(group_id, {
                "type": "group_status",
                "group_id": group_id,
                "status": status,
                "message": block_msg or "",
            })
        self.write({"code": 0 if ok else 1, "msg": msg})


class AdminImGroupsMembersHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        from app.models.im_group import ImGroupRepository
        group_id = int(self.get_argument("group_id", 0))
        if not group_id:
            return self.write({"code": 1, "msg": "参数错误"})
        members = ImGroupRepository.get_members(group_id)
        employees = ImGroupRepository.get_employees(group_id)
        group = ImGroupRepository.get_by_id_admin(group_id)
        self.write({"code": 0, "msg": "", "data": {"group": group, "members": members, "employees": employees}})


class AdminImGroupsAnnouncementHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        from app.models.im_group import ImGroupRepository
        from app.models.im_message import ImMessageRepository
        from app.controllers.im import broadcast_group
        group_id = int(self.get_body_argument("group_id", 0))
        announcement = self.get_body_argument("announcement", "").strip()
        if not group_id:
            return self.write({"code": 1, "msg": "参数错误"})
        ImGroupRepository.set_announcement(group_id, announcement)
        if announcement:
            sys_msg = ImMessageRepository.add(
                0, "group", group_id,
                f"【系统公告】{announcement}",
                msg_type="text",
            )
            sys_msg["sender_name"] = "系统公告"
            broadcast_group(group_id, {"type": "message", "data": sys_msg})
        self.write({"code": 0, "msg": "公告已发布"})


class AdminImMessagesHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_im_messages.html")


class AdminImMessagesListHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        from app.models.im_message import ImMessageRepository
        page = int(self.get_argument("page", 1))
        limit = int(self.get_argument("limit", 20))
        receiver_type = self.get_argument("receiver_type", "").strip()
        keyword = self.get_argument("keyword", "").strip()
        username = self.get_argument("username", "").strip()
        group_keyword = self.get_argument("group_keyword", "").strip()
        user_id = int(self.get_argument("user_id", 0))
        group_id = int(self.get_argument("group_id", 0))
        data, total = ImMessageRepository.admin_list(
            page,
            limit,
            receiver_type=receiver_type or None,
            keyword=keyword or None,
            username=username or None,
            group_keyword=group_keyword or None,
            user_id=user_id,
            group_id=group_id,
        )
        self.write({"code": 0, "msg": "", "count": total, "data": data})


class AdminImMessagesHistoryHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        from app.models.im_message import ImMessageRepository
        receiver_type = self.get_argument("receiver_type", "user").strip()
        receiver_id = int(self.get_argument("receiver_id", 0))
        peer_user_id = int(self.get_argument("peer_user_id", 0))
        before_id = int(self.get_argument("before_id", 0))
        limit = min(int(self.get_argument("limit", 100)), 200)
        if not receiver_id:
            return self.write({"code": 1, "msg": "参数错误"})
        if receiver_type not in ("user", "group"):
            return self.write({"code": 1, "msg": "无效的会话类型"})
        messages = ImMessageRepository.admin_get_history(
            receiver_type,
            receiver_id,
            peer_user_id=peer_user_id,
            limit=limit,
            before_id=before_id,
        )
        title = ""
        if receiver_type == "group":
            from app.models.im_group import ImGroupRepository
            group = ImGroupRepository.get_by_id_admin(receiver_id)
            title = group["name"] if group else f"群 #{receiver_id}"
        else:
            from app.models.user import UserRepository
            user = UserRepository.get_user_by_id(receiver_id)
            if peer_user_id:
                peer = UserRepository.get_user_by_id(peer_user_id)
                title = (user["username"] if user else str(receiver_id)) + " ↔ " + (
                    peer["username"] if peer else str(peer_user_id)
                )
            else:
                title = user["username"] if user else f"用户 #{receiver_id}"
        self.write({
            "code": 0,
            "msg": "",
            "data": {"title": title, "messages": messages},
        })


class AdminImFilesHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_im_files.html")


class AdminImFilesListHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        from app.models.im_file import ImFileRepository
        page = int(self.get_argument("page", 1))
        limit = int(self.get_argument("limit", 20))
        keyword = self.get_argument("keyword", "").strip()
        data, total = ImFileRepository.get_list(page, limit, keyword or None)
        self.write({"code": 0, "msg": "", "count": total, "data": data})


class AdminImFilesDeleteHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        from app.models.im_file import ImFileRepository
        file_id = int(self.get_body_argument("id", 0))
        if not file_id:
            return self.write({"code": 1, "msg": "参数错误"})
        if ImFileRepository.delete(file_id):
            self.write({"code": 0, "msg": "删除成功"})
        else:
            self.write({"code": 1, "msg": "文件不存在"})


class AdminImFilesPreviewHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        import os
        from app.models.im_file import ImFileRepository
        file_id = int(self.get_argument("id", 0))
        record = ImFileRepository.get_by_id(file_id)
        if not record:
            self.set_status(404)
            return self.write("文件不存在")
        path = ImFileRepository.get_full_path(record)
        if not os.path.exists(path):
            self.set_status(404)
            return self.write("文件不存在")
        ext = os.path.splitext(record["file_name"])[1].lower()
        if ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"):
            mime = "image/" + ext.lstrip(".")
            if ext == ".jpg":
                mime = "image/jpeg"
            self.set_header("Content-Type", mime)
        elif ext == ".pdf":
            self.set_header("Content-Type", "application/pdf")
        else:
            self.set_header("Content-Type", "text/plain; charset=utf-8")
        with open(path, "rb") as f:
            self.write(f.read())


class AdminImServersHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_im_servers.html")


class AdminImServersListHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        from app.models.im_file import ImServerRepository
        page = int(self.get_argument("page", 1))
        limit = int(self.get_argument("limit", 20))
        data, total = ImServerRepository.get_list(page, limit)
        self.write({"code": 0, "msg": "", "count": total, "data": data})


class AdminImServersAddHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        from app.models.im_file import ImServerRepository
        name = self.get_body_argument("name", "").strip()
        host = self.get_body_argument("host", "").strip()
        port = int(self.get_body_argument("port", 10086))
        status = int(self.get_body_argument("status", 1))
        priority = int(self.get_body_argument("priority", 0))
        current_load = int(self.get_body_argument("current_load", 0))
        if not name or not host:
            return self.write({"code": 1, "msg": "名称和主机不能为空"})
        ImServerRepository.add(name, host, port, status, priority, current_load)
        self.write({"code": 0, "msg": "添加成功"})


class AdminImServersUpdateHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        from app.models.im_file import ImServerRepository
        server_id = int(self.get_body_argument("id", 0))
        name = self.get_body_argument("name", "").strip()
        host = self.get_body_argument("host", "").strip()
        port = int(self.get_body_argument("port", 10086))
        status = int(self.get_body_argument("status", 1))
        priority = int(self.get_body_argument("priority", 0))
        current_load = int(self.get_body_argument("current_load", 0))
        if not server_id or not name or not host:
            return self.write({"code": 1, "msg": "参数错误"})
        ImServerRepository.update(server_id, name, host, port, status, priority, current_load)
        self.write({"code": 0, "msg": "更新成功"})


class AdminImServersDeleteHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        from app.models.im_file import ImServerRepository
        server_id = int(self.get_body_argument("id", 0))
        if not server_id:
            return self.write({"code": 1, "msg": "参数错误"})
        ImServerRepository.delete(server_id)
        self.write({"code": 0, "msg": "删除成功"})


class AdminEmployeeToolsHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_employee_tools.html")


class AdminEmployeeToolsListHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        from app.models.employee_tool import EmployeeToolRepository
        page = int(self.get_argument("page", 1))
        limit = int(self.get_argument("limit", 20))
        keyword = self.get_argument("keyword", "").strip()
        data, total = EmployeeToolRepository.get_list(page, limit, keyword or None)
        self.write({"code": 0, "msg": "", "count": total, "data": data})


class AdminEmployeeToolsAddHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        from app.models.employee_tool import EmployeeToolRepository
        name = self.get_body_argument("name", "").strip()
        tool_type = self.get_body_argument("tool_type", "api").strip()
        api_service_id = int(self.get_body_argument("api_service_id", 0))
        config = self.get_body_argument("config", "").strip()
        description = self.get_body_argument("description", "").strip()
        if not name:
            return self.write({"code": 1, "msg": "工具名称不能为空"})
        EmployeeToolRepository.add(name, tool_type, api_service_id, config, description)
        self.write({"code": 0, "msg": "添加成功"})


class AdminEmployeeToolsUpdateHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        from app.models.employee_tool import EmployeeToolRepository
        tool_id = int(self.get_body_argument("id", 0))
        name = self.get_body_argument("name", "").strip()
        tool_type = self.get_body_argument("tool_type", "api").strip()
        api_service_id = int(self.get_body_argument("api_service_id", 0))
        config = self.get_body_argument("config", "").strip()
        description = self.get_body_argument("description", "").strip()
        status = int(self.get_body_argument("status", 1))
        if not tool_id or not name:
            return self.write({"code": 1, "msg": "参数错误"})
        EmployeeToolRepository.update(
            tool_id, name, tool_type, api_service_id, config, description, status
        )
        self.write({"code": 0, "msg": "更新成功"})


class AdminEmployeeToolsDeleteHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        from app.models.employee_tool import EmployeeToolRepository
        tool_id = int(self.get_body_argument("id", 0))
        if not tool_id:
            return self.write({"code": 1, "msg": "参数错误"})
        EmployeeToolRepository.delete(tool_id)
        self.write({"code": 0, "msg": "删除成功"})


class AdminEmployeeToolsBindHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        from app.models.employee_tool import EmployeeToolRepository
        employee_id = int(self.get_body_argument("employee_id", 0))
        tool_ids_raw = self.get_body_argument("tool_ids", "[]")
        if not employee_id:
            return self.write({"code": 1, "msg": "参数错误"})
        try:
            tool_ids = json.loads(tool_ids_raw)
        except Exception:
            tool_ids = []
        EmployeeToolRepository.save_bindings(employee_id, tool_ids)
        self.write({"code": 0, "msg": "绑定成功"})


class AdminEmployeeToolsBindingsHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        from app.models.employee_tool import EmployeeToolRepository
        employee_id = int(self.get_argument("employee_id", 0))
        if not employee_id:
            return self.write({"code": 1, "msg": "参数错误"})
        tool_ids = EmployeeToolRepository.get_binding_ids(employee_id)
        self.write({"code": 0, "msg": "", "data": tool_ids})


# --- 自动化管理 ---

class AdminAutoManageHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_auto_manage.html")


class AdminAutoListHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1))
        limit = int(self.get_argument("limit", 20))
        tasks, total = AutoTaskRepository.get_all_tasks(page, limit)
        self.write({"code": 0, "msg": "", "count": total, "data": tasks})


class AdminAutoAddHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        name = self.get_body_argument("name", "").strip()
        task_type = self.get_body_argument("task_type", "collect").strip()
        cron_expression = self.get_body_argument("cron_expression", "").strip()
        interval_value = int(self.get_body_argument("interval_value", 60))
        interval_unit = self.get_body_argument("interval_unit", "seconds").strip()
        source_id = int(self.get_body_argument("source_id", 0))
        keyword = self.get_body_argument("keyword", "").strip()
        collect_count = int(self.get_body_argument("collect_count", 10))

        if not name:
            return self.write({"code": 1, "msg": "任务名称不能为空"})

        AutoTaskRepository.add_task(
            name, task_type, cron_expression if cron_expression else None,
            interval_value, interval_unit, source_id, keyword, collect_count
        )
        self.write({"code": 0, "msg": "添加成功"})


class AdminAutoUpdateHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        task_id = int(self.get_body_argument("id", 0))
        name = self.get_body_argument("name", "").strip()
        task_type = self.get_body_argument("task_type", "collect").strip()
        cron_expression = self.get_body_argument("cron_expression", "").strip()
        interval_value = int(self.get_body_argument("interval_value", 60))
        interval_unit = self.get_body_argument("interval_unit", "seconds").strip()
        source_id = int(self.get_body_argument("source_id", 0))
        keyword = self.get_body_argument("keyword", "").strip()
        collect_count = int(self.get_body_argument("collect_count", 10))
        status = int(self.get_body_argument("status", 0))

        if not task_id:
            return self.write({"code": 1, "msg": "任务ID不能为空"})

        AutoTaskRepository.update_task(
            task_id, name=name, task_type=task_type,
            cron_expression=cron_expression if cron_expression else None,
            interval_value=interval_value, interval_unit=interval_unit,
            source_id=source_id, keyword=keyword, collect_count=collect_count,
            status=status
        )
        self.write({"code": 0, "msg": "更新成功"})


class AdminAutoDeleteHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        task_id = int(self.get_body_argument("id", 0))
        if not task_id:
            return self.write({"code": 1, "msg": "参数错误"})
        AutoTaskRepository.delete_task(task_id)
        self.write({"code": 0, "msg": "删除成功"})


class AdminAutoStartHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        task_id = int(self.get_body_argument("id", 0))
        if not task_id:
            return self.write({"code": 1, "msg": "参数错误"})
        if start_task(task_id):
            self.write({"code": 0, "msg": "任务已启动"})
        else:
            self.write({"code": 1, "msg": "任务不存在"})


class AdminAutoStopHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        task_id = int(self.get_body_argument("id", 0))
        if not task_id:
            return self.write({"code": 1, "msg": "参数错误"})
        if stop_task(task_id):
            self.write({"code": 0, "msg": "任务已停止"})
        else:
            self.write({"code": 1, "msg": "任务不存在"})


class AdminAutoLogsHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        task_id = int(self.get_argument("task_id", 0))
        page = int(self.get_argument("page", 1))
        limit = int(self.get_argument("limit", 20))
        logs, total = AutoTaskRepository.get_task_logs(
            task_id if task_id else None, page, limit
        )
        self.write({"code": 0, "msg": "", "count": total, "data": logs})


class AdminAutoDataHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_auto_data.html")


class AdminAutoDataListHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1))
        limit = int(self.get_argument("limit", 20))
        keyword = self.get_argument("keyword", "").strip()
        data_list, total = WatchRepository.get_auto_data(
            page, limit, keyword if keyword else None
        )
        self.write({"code": 0, "msg": "", "count": total, "data": data_list})


class AdminAutoDataDeleteHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        import json
        ids_str = self.get_body_argument("ids", "[]")
        try:
            ids = json.loads(ids_str)
            if not ids:
                return self.write({"code": 1, "msg": "请选择要删除的数据"})
            WatchRepository.delete_data(ids)
            return self.write({"code": 0, "msg": "删除成功"})
        except Exception as e:
            return self.write({"code": 1, "msg": f"删除失败: {str(e)}"})


class AdminAutoRunNowHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        task_id = int(self.get_body_argument("id", 0))
        if not task_id:
            return self.write({"code": 1, "msg": "参数错误"})
        
        task = AutoTaskRepository.get_task_by_id(task_id)
        if not task:
            return self.write({"code": 1, "msg": "任务不存在"})
        
        try:
            total_saved = execute_auto_task(task_id)
            msg = f"手动执行完成"
            if total_saved > 0:
                msg += f"，采集到 {total_saved} 条新数据"
            else:
                msg += "，未采集到新数据"
            
            return self.write({
                "code": 0,
                "msg": msg,
                "count": total_saved,
                "need_announce": total_saved > 0
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return self.write({"code": 1, "msg": f"执行失败: {str(e)}"})


class AdminDbConfigHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_db_config.html")


class AdminDbConfigListHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        data = DbConfigRepository.get_list()
        self.write({"code": 0, "msg": "", "count": len(data), "data": data})


class AdminDbConfigAddHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        name = self.get_body_argument("name", "").strip()
        db_type = self.get_body_argument("db_type", "sqlite").strip()
        host = self.get_body_argument("host", "").strip()
        port = int(self.get_body_argument("port", 3306) or 3306)
        database_name = self.get_body_argument("database_name", "").strip()
        username = self.get_body_argument("username", "").strip()
        password = self.get_body_argument("password", "")

        if not name:
            return self.write({"code": 1, "msg": "配置名称不能为空"})
        if db_type == "mysql" and not database_name:
            return self.write({"code": 1, "msg": "MySQL 数据库名不能为空"})

        DbConfigRepository.add(name, db_type, host, port, database_name, username, password)
        self.write({"code": 0, "msg": "添加成功"})


class AdminDbConfigUpdateHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        config_id = int(self.get_body_argument("id", 0))
        name = self.get_body_argument("name", "").strip()
        db_type = self.get_body_argument("db_type", "sqlite").strip()
        host = self.get_body_argument("host", "").strip()
        port = int(self.get_body_argument("port", 3306) or 3306)
        database_name = self.get_body_argument("database_name", "").strip()
        username = self.get_body_argument("username", "").strip()
        password = self.get_body_argument("password", "")

        if not config_id or not name:
            return self.write({"code": 1, "msg": "参数错误"})
        if db_type == "mysql" and not database_name:
            return self.write({"code": 1, "msg": "MySQL 数据库名不能为空"})

        if not DbConfigRepository.update(config_id, name, db_type, host, port, database_name, username, password):
            return self.write({"code": 1, "msg": "配置不存在"})
        self.write({"code": 0, "msg": "更新成功"})


class AdminDbConfigSwitchHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        config_id = int(self.get_body_argument("id", 0))
        if not config_id:
            return self.write({"code": 1, "msg": "参数错误"})
        ok, msg = DbConfigRepository.switch(config_id)
        self.write({"code": 0 if ok else 1, "msg": msg})


class AdminDbConfigTestHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        if self.request.headers.get("Content-Type", "").startswith("application/json"):
            try:
                payload = json.loads(self.request.body.decode("utf-8") or "{}")
            except Exception:
                payload = {}
            ok, msg = DbConfigRepository.test_config(payload=payload)
            return self.write({"code": 0 if ok else 1, "msg": msg})

        config_id = int(self.get_body_argument("id", 0) or 0)
        if config_id:
            ok, msg = DbConfigRepository.test_config(config_id=config_id)
        else:
            ok, msg = DbConfigRepository.test_config(payload={
                "db_type": self.get_body_argument("db_type", "sqlite"),
                "host": self.get_body_argument("host", ""),
                "port": int(self.get_body_argument("port", 3306) or 3306),
                "database_name": self.get_body_argument("database_name", ""),
                "username": self.get_body_argument("username", ""),
                "password": self.get_body_argument("password", ""),
            })
        self.write({"code": 0 if ok else 1, "msg": msg})


class AdminDbConfigDeleteHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        config_id = int(self.get_body_argument("id", 0))
        if not config_id:
            return self.write({"code": 1, "msg": "参数错误"})
        ok, msg = DbConfigRepository.delete(config_id)
        self.write({"code": 0 if ok else 1, "msg": msg})


class AdminDbConfigSyncHandler(AdminBaseHandler):
    """从 SQLite 全量同步到指定 MySQL 配置（初始化与 SQLite 一致）。"""

    @tornado.web.authenticated
    def post(self):
        config_id = int(self.get_body_argument("id", 0))
        force = self.get_body_argument("force", "0") in ("1", "true", "True")
        if not config_id:
            return self.write({"code": 1, "msg": "参数错误"})
        target = DbConfigRepository.get_by_id(config_id)
        if not target:
            return self.write({"code": 1, "msg": "配置不存在"})
        if (target.get("db_type") or "").lower() != "mysql":
            return self.write({"code": 1, "msg": "仅 MySQL 配置支持从 SQLite 同步"})
        from app.models.db_sync import ensure_mysql_initialized
        try:
            ok, msg = ensure_mysql_initialized(target, force=force)
        except Exception as e:
            ok, msg = False, "同步异常: " + str(e)
        self.write({"code": 0 if ok else 1, "msg": msg})

