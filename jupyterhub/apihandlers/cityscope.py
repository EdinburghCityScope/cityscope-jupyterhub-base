import json
import random
import string

from tornado import gen, web

from .. import orm
from ..utils import admin_only
from .base import APIHandler
from subprocess import Popen
from os import urandom
from ..mysql_spawner import MySQLSpawner,MySQLProcessSpawner

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

        length = 13
        chars = string.ascii_letters + string.digits + "!$"
        random.seed = (urandom(1024))
        new_credential = "".join(chars[ord(urandom(1)) % len(chars)] for i in range(length))
        data_api_spawner = user.data_api_spawner
        new = yield data_api_spawner.start(credential=new_credential)
        if new:
            message = "Loopback startup complete, initial password is set to "+new_credential+" please make a safe note of this!"
        else:
            message = "Loopback startup complete"

        response = { 'message' : message}
        self.write(response)
        self.set_status(201)

    @gen.coroutine
    @admin_or_self
    def delete(self, name):
        user = self.find_user(name)
        print("Data API shutdown")
        data_api_spawner = user.data_api_spawner
        #try:
        yield data_api_spawner.stop()
        #except errors.NotFound:
        #    print("container not found")
        data_api_spawner.clear_state()
        self.set_status(201)

    @gen.coroutine
    @admin_or_self
    def put(self, name):
        user = self.find_user(name)
        print("Data API add dataset")
        data = json.loads(self.request.body.decode('utf-8'))
        data_api_spawner = user.data_api_spawner
        yield data_api_spawner.setup_data(data)
        response = { 'message' : 'Data setup complete'}
        self.write(response)
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
            if "pid" in status:
                self.set_status(200)
            elif "container_id" in status:
                self.set_status(200)
            else:
                self.set_status(204)
        else:
            self.set_status(204)



class UserMySQLAPIHandler(APIHandler):

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
        print("MySQL startup")

        length = 13
        chars = string.ascii_letters + string.digits + "!$"
        random.seed = (urandom(1024))
        new_credential = "".join(chars[ord(urandom(1)) % len(chars)] for i in range(length))
        hub = user.db.query(orm.Hub).first()
        mysql_spawner = MySQLProcessSpawner(
            user=user,
            db=user.db,
            hub=hub,
            authenticator=user.authenticator,
            config=user.settings.get('config'),
            )

        new = yield mysql_spawner.start(credential=new_credential)
        if new:
            message = "MySQL startup complete, initial password is set to "+new_credential+" please make a safe note of this!"
        else:
            message = "MySQL startup complete"

        response = { 'message' : message}
        self.write(response)
        self.set_status(201)

    @gen.coroutine
    @admin_or_self
    def delete(self, name):
        user = self.find_user(name)
        print("MySQL shutdown")
        mysql_spawner = user.mysql_spawner
        #try:
        yield mysql_spawner.stop()
        #except errors.NotFound:
        #    print("container not found")
        mysql_spawner.clear_state()
        self.set_status(201)

    @gen.coroutine
    @admin_or_self
    def put(self, name):
        user = self.find_user(name)
        response = { 'message' : 'Cannot edit MySQL config: setup complete'}
        self.write(response)
        self.set_status(201)

    @gen.coroutine
    @admin_or_self
    def get(self,name):
        user = self.find_user(name)
        print("MySQL status")
        mysql_spawner = user.mysql_spawner
        status = mysql_spawner.get_state()
        print(status)
        if status is not None:
            if "pid" in status:
                self.set_status(200)
            elif "container_id" in status:
                self.set_status(200)
            else:
                self.set_status(204)
        else:
            self.set_status(204)



default_handlers = [
    (r"/api/users/([^/]+)/loopback", UserLoopbackAPIHandler),
    (r"/api/users/([^/]+)/mysql", UserMySQLAPIHandler)
]
