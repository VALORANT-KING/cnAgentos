import tornado.web

from app.controllers.base import BaseHandler


class IndexHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.redirect("/home")


class HomePortalHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("home.html", username=self.current_user)