import tornado.web
from app.controllers.base import BaseHandler
from app.models.user import UserRepository


class LoginHandler(BaseHandler):
    def get(self):
        user = self.get_current_user()
        if user:
            self.redirect("/chat")
        else:
            self.render("login.html", title="登录", error=None)

    def post(self):
        username = (self.get_body_argument("username", "") or "").strip()
        password = self.get_body_argument("password", "")

        if not username or not password:
            return self.render("login.html", title="登录", error="用户名或密码不能为空")

        if not UserRepository.verify_user(username, password):
            return self.render("login.html", title="登录", error="用户名或密码错误")

        self.set_secure_cookie("username", username)
        self.redirect("/chat")


class LogoutHandler(BaseHandler):
    def post(self):
        self.clear_cookie("username")
        self.redirect("/auth/login")


class RegisterHandler(BaseHandler):
    def get(self):
        user = self.get_current_user()
        if user:
            self.redirect("/chat")
        else:
            self.render("register.html", title="注册", error=None)

    def post(self):
        username = (self.get_body_argument("username", "") or "").strip()
        password = self.get_body_argument("password", "")
        confirm = self.get_body_argument("confirm", "")

        if not username or not password:
            return self.render("register.html", title="注册", error="用户名和密码不能为空")

        if len(username) < 2:
            return self.render("register.html", title="注册", error="用户名至少2个字符")

        if len(password) < 6:
            return self.render("register.html", title="注册", error="密码至少6个字符")

        if password != confirm:
            return self.render("register.html", title="注册", error="两次密码输入不一致")

        existing = UserRepository.get_user_by_username(username)
        if existing:
            return self.render("register.html", title="注册", error="用户名已存在")

        ok = UserRepository.create_user(username, password, role="user")
        if not ok:
            return self.render("register.html", title="注册", error="注册失败，请稍后重试")

        self.set_secure_cookie("username", username)
        self.redirect("/chat")
