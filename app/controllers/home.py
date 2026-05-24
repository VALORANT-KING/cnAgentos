import tornado.web

from app.controllers.base import BaseHandler

class IndexHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.redirect("/chat")