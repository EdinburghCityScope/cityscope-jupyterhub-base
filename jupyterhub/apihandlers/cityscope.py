import json

from tornado import gen, web

from .. import orm
from ..utils import admin_only
from .base import APIHandler
from subprocess import Popen

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
        print("Data API startup")
        data_api_spawner = user.data_api_spawner
        data_api_spawner.start()
        self.set_status(201)

    @gen.coroutine
    @admin_or_self
    def delete(self, name):
        user = self.find_user(name)
        print("Data API shutdown")
        data_api_spawner = user.data_api_spawner
        data_api_spawner.stop()
        data_api_spawner.clear_state()
        self.set_status(201)

    @gen.coroutine
    @admin_or_self
    def put(self, name):
        print("Data API add dataset")
        self.set_status(201)

    @gen.coroutine
    @admin_or_self
    def get(self,name):
        user = self.find_user(name)
        print("Data API status")
        data_api_spawner = user.data_api_spawner
        status = data_api_spawner.get_state()
        print(status)
        if status is not None:
            if "pid" not in status:
                self.set_status(404)
            else:
                self.set_status(201)
        else:
            self.set_status(404)

default_handlers = [
    (r"/api/users/([^/]+)/loopback", UserLoopbackAPIHandler)
]
