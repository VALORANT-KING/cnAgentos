import tornado.web

from app.controllers.base import BaseHandler


class IndexHandler(tornado.web.RequestHandler):
    """主官网首页，无需登录即可访问。"""

    def get(self):
        self.render("portal.html")


class HomePortalHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("home.html", username=self.current_user)