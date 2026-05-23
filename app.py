# 程序的主入口
# 承担服务器容器+程序作用
# 服务器容器：提供http容器服务，程序放置于该容器中运行
# 程序：本体-智能瞭望与智能问数系统 B/s架构
import os
import tornado.ioloop
import tornado.web
from tornado.httpserver import HTTPServer

# 取消BaseHandler导入注释（PrivateHandler需要继承它）
from app.controllers.base import BaseHandler
#引入auth - controller层
from app.controllers.auth import LoginHandler
from app.controllers.auth import LogoutHandler
from app.controllers.home import IndexHandler
#引入db - model层
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
            (r"/auth/login", LoginHandler),
            (r"/auth/logout", LogoutHandler)
        ], **settings)

if __name__ == "__main__":
    init_db()
    app = make_app()
    server = HTTPServer(app)
    server.bind(10086)
    # 自动CPU核心数
    server.start()

    print("====== Server 启动成功 ======= 端口：10086 =====",flush=True)
    print("登录地址：http://127.0.0.1:10086/auth/login", flush=True)
    tornado.ioloop.IOLoop.current().start()