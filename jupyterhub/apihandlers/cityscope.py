import json

from tornado import gen, web

from .. import orm
from ..utils import admin_only
from .base import APIHandler

class UserLoopbackAPIHandler(APIHandler):

    def admin_or_self(method):
        """Decorator for restricting access to either the target user or admin"""
        def m(self, name):
            current = self.get_current_user()
            if current is None:
                raise web.HTTPError(403)
            if not (current.name == name or current.admin):
                raise web.HTTPError(403)

            # raise 404 if not found
            if not self.find_user(name):
                raise web.HTTPError(404)
            return method(self, name)
        return m

    @gen.coroutine
    @admin_or_self
    def post(self, name):
        user = self.find_user(name)
        self.set_status(201)

    @gen.coroutine
    @admin_or_self
    def delete(self, name):
        self.set_status(201)

    @gen.coroutine
    @admin_or_self
    def put(self, name):
        self.set_status(201)

    @gen.coroutine
    @admin_or_self
    def get(self,name):
        self.set_status(201)

default_handlers = [
    (r"/api/users/([^/]+)/loopback", UserLoopbackAPIHandler)
]
