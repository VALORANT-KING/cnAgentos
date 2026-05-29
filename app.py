# 程序的主入口
# 承担服务器容器+程序作用
# 服务器容器：提供http容器服务，程序放置于该容器中运行
# 程序：本体-智能瞭望与智能问数系统 B/s架构
import os
import sys

# 项目根目录（相对路径解析为绝对路径，保证任意机器可运行）
_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

# 使用项目 env 内嵌 Python 时，依赖已安装在 env/Lib/site-packages
_site = os.path.join(_root, "env", "Lib", "site-packages")
if os.path.isdir(_site) and _site not in sys.path:
    sys.path.insert(0, _site)

import tornado.ioloop
import tornado.web
from tornado.httpserver import HTTPServer

# 取消BaseHandler导入注释（PrivateHandler需要继承它）
from app.controllers.base import BaseHandler
from app.controllers.auth import LoginHandler
from app.controllers.auth import LogoutHandler
from app.controllers.home import IndexHandler
from app.controllers.admin import AdminLoginHandler
from app.controllers.admin import AdminLogoutHandler
from app.controllers.admin import AdminIndexHandler
from app.controllers.admin import AdminHomeHandler
from app.controllers.admin import AdminHomeStatsHandler
from app.controllers.admin import AdminUserManageHandler
from app.controllers.admin import AdminUserListHandler
from app.controllers.admin import AdminUserAddHandler
from app.controllers.admin import AdminUserUpdateHandler
from app.controllers.admin import AdminUserDeleteHandler
from app.controllers.admin import AdminMenuHandler
from app.controllers.admin import AdminModuleManageHandler
from app.controllers.admin import AdminModuleListHandler
from app.controllers.admin import AdminModuleAddHandler
from app.controllers.admin import AdminModuleUpdateHandler
from app.controllers.admin import AdminModuleDeleteHandler
from app.controllers.admin import AdminRoleManageHandler
from app.controllers.admin import AdminRoleListHandler
from app.controllers.admin import AdminRoleAddHandler
from app.controllers.admin import AdminRoleUpdateHandler
from app.controllers.admin import AdminRoleDeleteHandler
from app.controllers.admin import AdminRoleSelectHandler
from app.controllers.admin import AdminPermissionManageHandler
from app.controllers.admin import AdminPermissionLoadHandler
from app.controllers.admin import AdminPermissionSaveHandler
from app.controllers.admin import AdminModelManageHandler
from app.controllers.admin import AdminModelListHandler
from app.controllers.admin import AdminModelAddHandler
from app.controllers.admin import AdminModelUpdateHandler
from app.controllers.admin import AdminModelDeleteHandler
from app.controllers.admin import AdminModelSetDefaultHandler
from app.controllers.admin import AdminModelChatHandler
from app.controllers.admin import AdminModelChatStreamHandler
from app.controllers.admin import AdminWatchSourceHandler
from app.controllers.admin import AdminWatchSourceListHandler
from app.controllers.admin import AdminWatchSourceAddHandler
from app.controllers.admin import AdminWatchSourceUpdateHandler
from app.controllers.admin import AdminWatchSourceDeleteHandler
from app.controllers.admin import AdminWatchCollectHandler
from app.controllers.admin import AdminWatchCollectSourcesHandler
from app.controllers.admin import AdminWatchDoCollectHandler
from app.controllers.admin import AdminWatchDataHandler
from app.controllers.admin import AdminWatchDataListHandler
from app.controllers.admin import AdminWatchDataDeleteHandler
from app.controllers.admin import AdminApiManageHandler
from app.controllers.admin import AdminApiListHandler
from app.controllers.admin import AdminApiAddHandler
from app.controllers.admin import AdminApiUpdateHandler
from app.controllers.admin import AdminApiDeleteHandler
from app.controllers.admin import AdminEmployeeManageHandler
from app.controllers.admin import AdminEmployeeListHandler
from app.controllers.admin import AdminEmployeeAddHandler
from app.controllers.admin import AdminEmployeeUpdateHandler
from app.controllers.admin import AdminEmployeeDeleteHandler
from app.controllers.admin import AdminImGroupsHandler
from app.controllers.admin import AdminImGroupsListHandler
from app.controllers.admin import AdminImGroupsDissolveHandler
from app.controllers.admin import AdminImGroupsBanHandler
from app.controllers.admin import AdminImGroupsMembersHandler
from app.controllers.admin import AdminImGroupsAnnouncementHandler
from app.controllers.admin import AdminImMessagesHandler
from app.controllers.admin import AdminImMessagesListHandler
from app.controllers.admin import AdminImMessagesHistoryHandler
from app.controllers.admin import AdminImFilesHandler
from app.controllers.admin import AdminImFilesListHandler
from app.controllers.admin import AdminImFilesDeleteHandler
from app.controllers.admin import AdminImFilesPreviewHandler
from app.controllers.admin import AdminImServersHandler
from app.controllers.admin import AdminImServersListHandler
from app.controllers.admin import AdminImServersAddHandler
from app.controllers.admin import AdminImServersUpdateHandler
from app.controllers.admin import AdminImServersDeleteHandler
from app.controllers.admin import AdminEmployeeToolsHandler
from app.controllers.admin import AdminEmployeeToolsListHandler
from app.controllers.admin import AdminEmployeeToolsAddHandler
from app.controllers.admin import AdminEmployeeToolsUpdateHandler
from app.controllers.admin import AdminEmployeeToolsDeleteHandler
from app.controllers.admin import AdminEmployeeToolsBindHandler
from app.controllers.admin import AdminEmployeeToolsBindingsHandler
from app.controllers.admin import AdminAutoManageHandler
from app.controllers.admin import AdminAutoListHandler
from app.controllers.admin import AdminAutoAddHandler
from app.controllers.admin import AdminAutoUpdateHandler
from app.controllers.admin import AdminAutoDeleteHandler
from app.controllers.admin import AdminAutoStartHandler
from app.controllers.admin import AdminAutoStopHandler
from app.controllers.admin import AdminAutoLogsHandler
from app.controllers.admin import AdminAutoDataHandler
from app.controllers.admin import AdminAutoDataListHandler
from app.controllers.admin import AdminAutoDataDeleteHandler
from app.controllers.admin import AdminAutoRunNowHandler
from app.controllers.admin import AdminDbConfigHandler
from app.controllers.admin import AdminDbConfigListHandler
from app.controllers.admin import AdminDbConfigAddHandler
from app.controllers.admin import AdminDbConfigUpdateHandler
from app.controllers.admin import AdminDbConfigSwitchHandler
from app.controllers.admin import AdminDbConfigTestHandler
from app.controllers.admin import AdminDbConfigDeleteHandler
from app.controllers.admin import AdminDbConfigSyncHandler
from app.scheduler import init_scheduler, shutdown_scheduler
from app.controllers.chat import ChatIndexHandler
from app.controllers.chat import ChatSessionListHandler
from app.controllers.chat import ChatSessionAddHandler
from app.controllers.chat import ChatSessionDeleteHandler
from app.controllers.chat import ChatHistoryHandler
from app.controllers.chat import ChatEmployeeListHandler
from app.controllers.chat import ChatModelListHandler
from app.controllers.chat import ChatSendHandler
from app.controllers.chat import ChatStreamHandler
from app.controllers.auth import RegisterHandler
from app.controllers.home import HomePortalHandler
from app.controllers.im import ImIndexHandler
from app.controllers.im import ImWebSocketHandler
from app.controllers.im import ImFriendSearchHandler
from app.controllers.im import ImFriendAddHandler
from app.controllers.im import ImFriendListHandler
from app.controllers.im import ImFriendRequestsHandler
from app.controllers.im import ImFriendAcceptHandler
from app.controllers.im import ImFriendRejectHandler
from app.controllers.im import ImFriendDeleteHandler
from app.controllers.im import ImGroupCreateHandler
from app.controllers.im import ImGroupListHandler
from app.controllers.im import ImGroupJoinHandler
from app.controllers.im import ImGroupMembersHandler
from app.controllers.im import ImGroupInviteHandler
from app.controllers.im import ImMessageHistoryHandler
from app.controllers.im import ImConversationsHandler
from app.controllers.im import ImFileUploadHandler
from app.controllers.im import ImFileDownloadHandler
from app.controllers.im import ImServerListHandler
from app.controllers.im import ImServerHealthHandler
from app.controllers.im import ImEmployeeListHandler
from app.controllers.im import ImEmployeeCallHandler
from app.controllers.screen import ScreenStatsHandler
from app.controllers.screen import ScreenWordcloudHandler
from app.controllers.screen import ScreenEarthDataHandler
from app.controllers.screen import ScreenAnalyzeHandler
from app.controllers.screen import ScreenDashboardHandler
from app.controllers.screen import ScreenWordDetailHandler
from app.controllers.screen import ScreenLocationNewsHandler
from app.models.db import init_db


# 取消HealthHandler注释（解决/abc、/等路径404）
class HealthHandler(tornado.web.RequestHandler):
    def get(self):
        self.write({"status":"ok"})

# class LoginHandler(tornado.web.RequestHandler):
#     def get(self):
#         self.write(f"""<h3>模拟登录验证测试BaseHandler</h3>

#             <form method="post">

#             <button type="submit">登录admin</button>
#             """
#             + self.xsrf_form_html() +
#             """
#             </form>
#             """)
#         def post(self):
#             next_url = self.get_argument("next", "/private")
#             self.set_secure_cookie("username", "admin")
#             # 写完安全的cookie以后，跳转到目标地址
#             self.redirect(next_url)


# 取消PrivateHandler注释（解决登录成功后跳转到/private的404）
class PrivateHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.write(self.current_user)


def make_app():
    # return tornado.web.Application([
    #     ("/abc",HealthHandler),
    #     ("/login.jsp",HealthHandler),
    #     ("/",HealthHandler),
    #     ("/login.php",HealthHandler)
    # ],debug=True)
    # return tornado.web.Application([
    #     (r"/", LoginHandler),
    #     (r"/login",LoginHandler),
    #     (r"/abc", HealthHandler),
    #     (r"/private", PrivateHandler)
    # ],
    # cookie_secret="demo-cookie-secret-change-me",
    # login_url = "/login",
    # xsrf_cookies=True,
    # debug=True
    # )
    base_url = os.path.dirname(os.path.abspath(__file__))
    settings = dict(
        # 预留view层内容配置
        template_path = os.path.join(base_url, "app", "templates"),
        static_path = os.path.join(base_url, "app", "static"),  
        cookie_secret="demo-cookie-secret-change-me",
        login_url="/auth/login",
        xsrf_cookies=True,
        debug=True,
        autoreload=True
    )
    # 添加所有缺失的路由
    return tornado.web.Application([
            (r"/", IndexHandler),
            (r"/home", HomePortalHandler),
            (r"/auth/login", LoginHandler),
            (r"/auth/logout", LogoutHandler),
            (r"/admin/login", AdminLoginHandler),
            (r"/admin/logout", AdminLogoutHandler),
            (r"/admin", AdminIndexHandler),
            (r"/admin/home", AdminHomeHandler),
            (r"/admin/home/stats", AdminHomeStatsHandler),
            (r"/admin/menu", AdminMenuHandler),
            (r"/admin/user/manage", AdminUserManageHandler),
            (r"/admin/user/list", AdminUserListHandler),
            (r"/admin/user/add", AdminUserAddHandler),
            (r"/admin/user/update", AdminUserUpdateHandler),
            (r"/admin/user/delete", AdminUserDeleteHandler),
            (r"/admin/module/manage", AdminModuleManageHandler),
            (r"/admin/module/list", AdminModuleListHandler),
            (r"/admin/module/add", AdminModuleAddHandler),
            (r"/admin/module/update", AdminModuleUpdateHandler),
            (r"/admin/module/delete", AdminModuleDeleteHandler),
            (r"/admin/role/manage", AdminRoleManageHandler),
            (r"/admin/role/list", AdminRoleListHandler),
            (r"/admin/role/add", AdminRoleAddHandler),
            (r"/admin/role/update", AdminRoleUpdateHandler),
            (r"/admin/role/delete", AdminRoleDeleteHandler),
            (r"/admin/role/select", AdminRoleSelectHandler),
            (r"/admin/permission/manage", AdminPermissionManageHandler),
            (r"/admin/permission/load", AdminPermissionLoadHandler),
            (r"/admin/permission/save", AdminPermissionSaveHandler),
            (r"/admin/model/manage", AdminModelManageHandler),
            (r"/admin/model/list", AdminModelListHandler),
            (r"/admin/model/add", AdminModelAddHandler),
            (r"/admin/model/update", AdminModelUpdateHandler),
            (r"/admin/model/delete", AdminModelDeleteHandler),
            (r"/admin/model/setdefault", AdminModelSetDefaultHandler),
            (r"/admin/model/chat", AdminModelChatHandler),
            (r"/admin/model/chatstream", AdminModelChatStreamHandler),
            (r"/admin/watch/source", AdminWatchSourceHandler),
            (r"/admin/watch/source/list", AdminWatchSourceListHandler),
            (r"/admin/watch/source/add", AdminWatchSourceAddHandler),
            (r"/admin/watch/source/update", AdminWatchSourceUpdateHandler),
            (r"/admin/watch/source/delete", AdminWatchSourceDeleteHandler),
            (r"/admin/watch/collect", AdminWatchCollectHandler),
            (r"/admin/watch/collect/sources", AdminWatchCollectSourcesHandler),
            (r"/admin/watch/docollect", AdminWatchDoCollectHandler),
            (r"/admin/watch/data", AdminWatchDataHandler),
            (r"/admin/watch/data/list", AdminWatchDataListHandler),
            (r"/admin/watch/data/delete", AdminWatchDataDeleteHandler),
            (r"/admin/api/manage", AdminApiManageHandler),
            (r"/admin/api/list", AdminApiListHandler),
            (r"/admin/api/add", AdminApiAddHandler),
            (r"/admin/api/update", AdminApiUpdateHandler),
            (r"/admin/api/delete", AdminApiDeleteHandler),
            (r"/admin/employee/manage", AdminEmployeeManageHandler),
            (r"/admin/employee/list", AdminEmployeeListHandler),
            (r"/admin/employee/add", AdminEmployeeAddHandler),
            (r"/admin/employee/update", AdminEmployeeUpdateHandler),
            (r"/admin/employee/delete", AdminEmployeeDeleteHandler),
            (r"/admin/im/groups", AdminImGroupsHandler),
            (r"/admin/im/groups/list", AdminImGroupsListHandler),
            (r"/admin/im/groups/dissolve", AdminImGroupsDissolveHandler),
            (r"/admin/im/groups/ban", AdminImGroupsBanHandler),
            (r"/admin/im/groups/members", AdminImGroupsMembersHandler),
            (r"/admin/im/groups/announcement", AdminImGroupsAnnouncementHandler),
            (r"/admin/im/messages", AdminImMessagesHandler),
            (r"/admin/im/messages/list", AdminImMessagesListHandler),
            (r"/admin/im/messages/history", AdminImMessagesHistoryHandler),
            (r"/admin/im/files", AdminImFilesHandler),
            (r"/admin/im/files/list", AdminImFilesListHandler),
            (r"/admin/im/files/delete", AdminImFilesDeleteHandler),
            (r"/admin/im/files/preview", AdminImFilesPreviewHandler),
            (r"/admin/im/servers", AdminImServersHandler),
            (r"/admin/im/servers/list", AdminImServersListHandler),
            (r"/admin/im/servers/add", AdminImServersAddHandler),
            (r"/admin/im/servers/update", AdminImServersUpdateHandler),
            (r"/admin/im/servers/delete", AdminImServersDeleteHandler),
            (r"/admin/employee/tools", AdminEmployeeToolsHandler),
            (r"/admin/employee/tools/list", AdminEmployeeToolsListHandler),
            (r"/admin/employee/tools/add", AdminEmployeeToolsAddHandler),
            (r"/admin/employee/tools/update", AdminEmployeeToolsUpdateHandler),
            (r"/admin/employee/tools/delete", AdminEmployeeToolsDeleteHandler),
            (r"/admin/employee/tools/bind", AdminEmployeeToolsBindHandler),
            (r"/admin/employee/tools/bindings", AdminEmployeeToolsBindingsHandler),
            (r"/admin/auto/manage", AdminAutoManageHandler),
            (r"/admin/auto/list", AdminAutoListHandler),
            (r"/admin/auto/add", AdminAutoAddHandler),
            (r"/admin/auto/update", AdminAutoUpdateHandler),
            (r"/admin/auto/delete", AdminAutoDeleteHandler),
            (r"/admin/auto/start", AdminAutoStartHandler),
            (r"/admin/auto/stop", AdminAutoStopHandler),
            (r"/admin/auto/logs", AdminAutoLogsHandler),
            (r"/admin/auto/data", AdminAutoDataHandler),
            (r"/admin/auto/data/list", AdminAutoDataListHandler),
            (r"/admin/auto/data/delete", AdminAutoDataDeleteHandler),
            (r"/admin/auto/run", AdminAutoRunNowHandler),
            (r"/admin/db/config", AdminDbConfigHandler),
            (r"/admin/db/config/list", AdminDbConfigListHandler),
            (r"/admin/db/config/add", AdminDbConfigAddHandler),
            (r"/admin/db/config/update", AdminDbConfigUpdateHandler),
            (r"/admin/db/config/switch", AdminDbConfigSwitchHandler),
            (r"/admin/db/config/test", AdminDbConfigTestHandler),
            (r"/admin/db/config/delete", AdminDbConfigDeleteHandler),
            (r"/admin/db/config/sync", AdminDbConfigSyncHandler),
            (r"/chat", ChatIndexHandler),
            (r"/api/chat/sessions", ChatSessionListHandler),
            (r"/api/chat/session/add", ChatSessionAddHandler),
            (r"/api/chat/session/delete", ChatSessionDeleteHandler),
            (r"/api/chat/history", ChatHistoryHandler),
            (r"/api/chat/send", ChatSendHandler),
            (r"/api/chat/stream", ChatStreamHandler),
            (r"/api/employee/list", ChatEmployeeListHandler),
            (r"/api/model/list", ChatModelListHandler),
            (r"/auth/register", RegisterHandler),
            (r"/im", ImIndexHandler),
            (r"/ws/im", ImWebSocketHandler),
            (r"/api/im/friends/search", ImFriendSearchHandler),
            (r"/api/im/friends/add", ImFriendAddHandler),
            (r"/api/im/friends/list", ImFriendListHandler),
            (r"/api/im/friends/requests", ImFriendRequestsHandler),
            (r"/api/im/friends/accept", ImFriendAcceptHandler),
            (r"/api/im/friends/reject", ImFriendRejectHandler),
            (r"/api/im/friends/delete", ImFriendDeleteHandler),
            (r"/api/im/groups/create", ImGroupCreateHandler),
            (r"/api/im/groups/list", ImGroupListHandler),
            (r"/api/im/groups/join", ImGroupJoinHandler),
            (r"/api/im/groups/members", ImGroupMembersHandler),
            (r"/api/im/groups/invite", ImGroupInviteHandler),
            (r"/api/im/messages/history", ImMessageHistoryHandler),
            (r"/api/im/conversations", ImConversationsHandler),
            (r"/api/im/files/upload", ImFileUploadHandler),
            (r"/api/im/files/download", ImFileDownloadHandler),
            (r"/api/im/servers/list", ImServerListHandler),
            (r"/api/im/health", ImServerHealthHandler),
            (r"/api/im/employee/call", ImEmployeeCallHandler),
            (r"/api/screen/stats", ScreenStatsHandler),
            (r"/api/screen/wordcloud", ScreenWordcloudHandler),
            (r"/api/screen/earth-data", ScreenEarthDataHandler),
            (r"/api/screen/analyze", ScreenAnalyzeHandler),
            (r"/api/screen/word-detail", ScreenWordDetailHandler),
            (r"/api/screen/location-news", ScreenLocationNewsHandler),
            (r"/screen/dashboard", ScreenDashboardHandler),
        ], **settings)

if __name__ == "__main__":
    init_db()
    app = make_app()
    # Windows 下建议直接使用 app.listen
    app.listen(10086, address="0.0.0.0")

    # 初始化自动化任务调度器
    init_scheduler()

    print("====== Server 启动成功 ======= 端口：10086 (局域网可访问) =====", flush=True)
    print("官方网站首页：http://127.0.0.1:10086/", flush=True)
    print("用户登录地址：http://127.0.0.1:10086/auth/login", flush=True)
    print("用户首页：http://127.0.0.1:10086/home", flush=True)
    print("智能聊天：http://127.0.0.1:10086/im", flush=True)
    print("管理后台地址：http://127.0.0.1:10086/admin/login", flush=True)
    try:
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        # 关闭调度器
        shutdown_scheduler()
        print("Server 已停止")