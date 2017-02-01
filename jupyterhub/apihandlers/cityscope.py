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
            message = "API startup complete. To view your password, click the cog to the right and select Show my API password."
        else:
            message = "API startup complete"

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
        data_api_spawner = user.data_api_spawner
        if (self.get_arguments('credential')):
            print("Data API get credential")
            status = yield data_api_spawner.get_container()
            self.set_status(200)
            for index,arg in enumerate(status['Args']):
                if arg == '-credential':
                    self.write(status['Args'][index+1])
        else:
            print("Data API status")
            status = yield data_api_spawner.get_state()
            if status is not None:
                if "pid" in status:
                    self.set_status(200)
                elif "container_id" in status:
                    self.set_status(200)
                elif "container_state" in status:
                    self.set_status(204)
                else:
                    self.set_status(404)
            else:
                self.set_status(404)

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

        length = 13
        chars = string.ascii_letters + string.digits + "!$"
        random.seed = (urandom(1024))
        new_credential = "".join(chars[ord(urandom(1)) % len(chars)] for i in range(length))
        mysql_spawner = user.mysql_spawner

        new = yield mysql_spawner.start(credential=new_credential)
        if new:
            message = "MySQL startup complete, initial password is set to "+new_credential+" please make a safe note of this."
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
        message = "MySQL shutdown"
        response = { 'message' : message}
        self.write(response)
        self.set_status(201)

    @gen.coroutine
    @admin_or_self
    def put(self, name):
        user = self.find_user(name)
        response = { 'message' : 'Edit MySQL config via API Forbidden: setup complete'}
        self.write(response)
        self.set_status(401)

    @gen.coroutine
    @admin_or_self
    def get(self,name):
        user = self.find_user(name)
        mysql_spawner = user.mysql_spawner
        status = mysql_spawner.get_state()
        print("MySQL Status: status")
        if status is not None:
            if "pid" in status:
                self.set_status(200)
            elif "container_id" in status:
                self.set_status(200)
            else:
                self.set_status(204)
        else:
            self.set_status(204)




class UserWordpressAPIHandler(APIHandler):

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

        length = 13
        chars = string.ascii_letters + string.digits + "!$"
        random.seed = (urandom(1024))
        new_credential = "".join(chars[ord(urandom(1)) % len(chars)] for i in range(length))
        wordpress_spawner = user.wordpress_spawner

        new = yield wordpress_spawner.start(credential=new_credential)
        if new:
            message = "We're setting up a Wordpress instance for you, it may take up to an hour for this to become available. To view your password, click the cog to the right and select Show my Blog password."
        else:
            message = "Wordpress startup complete"

        response = { 'message' : message}
        self.write(response)
        self.set_status(201)

    @gen.coroutine
    @admin_or_self
    def delete(self, name):
        user = self.find_user(name)
        print("Wordpress shutdown")
        wordpress_spawner = user.wordpress_spawner
        #try:
        yield wordpress_spawner.stop()
        #except errors.NotFound:
        #    print("container not found")
        wordpress_spawner.clear_state()
        message = "Wordpress shutdown"
        response = { 'message' : message}
        self.write(response)
        self.set_status(201)

    @gen.coroutine
    @admin_or_self
    def put(self, name):
        user = self.find_user(name)
        response = { 'message' : 'Edit Wordpress config via API Forbidden: setup complete'}
        self.write(response)
        self.set_status(401)

    @gen.coroutine
    @admin_or_self
    def get(self,name):
        user = self.find_user(name)
        wordpress_spawner = user.wordpress_spawner
        if (self.get_arguments('credential')):
            print("Blog get credential")
            status = yield wordpress_spawner.get_container()
            self.set_status(200)
            for index,arg in enumerate(status['Args']):
                if arg == '-credential':
                    self.write(status['Args'][index+1])
        else:
            status = yield wordpress_spawner.get_state()
            print("Wordpress Status: status")
            if status is not None:
                if "pid" in status:
                    self.set_status(200)
                elif "container_id" in status:
                    self.set_status(200)
                elif "container_state" in status:
                    self.set_status(204)
                else:
                    self.set_status(404)
            else:
                self.set_status(404)

class UserFieldtripAPIHandler(APIHandler):

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

        length = 13
        chars = string.ascii_letters + string.digits + "!$"
        random.seed = (urandom(1024))
        new_credential = "".join(chars[ord(urandom(1)) % len(chars)] for i in range(length))
        fieldtrip_spawner = user.fieldtrip_spawner

        new = yield fieldtrip_spawner.start(credential=new_credential)
        if new:
            message = "Fieldtrip startup complete. To view your password, click the cog to the right and select Show my Fieldtrip password."
        else:
            message = "Fieldtrip startup complete"

        response = { 'message' : message}
        self.write(response)
        self.set_status(201)

    @gen.coroutine
    @admin_or_self
    def delete(self, name):
        user = self.find_user(name)
        print("Fieldtrip shutdown")
        fieldtrip_spawner = user.fieldtrip_spawner
        #try:
        yield fieldtrip_spawner.stop()
        #except errors.NotFound:
        #    print("container not found")
        fieldtrip_spawner.clear_state()
        message = "Fieldtrip shutdown"
        response = { 'message' : message}
        self.write(response)
        self.set_status(201)

    @gen.coroutine
    @admin_or_self
    def put(self, name):
        user = self.find_user(name)
        response = { 'message' : 'Edit Fieldtrip config via API Forbidden: setup complete'}
        self.write(response)
        self.set_status(401)

    @gen.coroutine
    @admin_or_self
    def get(self,name):
        user = self.find_user(name)
        fieldtrip_spawner = user.fieldtrip_spawner
        if (self.get_arguments('credential')):
            print("Fieldtrip get credential")
            status = yield fieldtrip_spawner.get_container()
            self.set_status(200)
            for index,arg in enumerate(status['Args']):
                if arg == '-credential':
                    self.write(status['Args'][index+1])
        else:
            status = yield fieldtrip_spawner.get_state()
            print("Fieldtrip Status: status")
            if status is not None:
                if "pid" in status:
                    self.set_status(200)
                elif "container_id" in status:
                    self.set_status(200)
                elif "container_state" in status:
                    self.set_status(204)
                else:
                    self.set_status(404)
            else:
                self.set_status(404)

default_handlers = [
    (r"/api/users/([^/]+)/loopback", UserLoopbackAPIHandler),
    (r"/api/users/([^/]+)/mysql", UserMySQLAPIHandler),
    (r"/api/users/([^/]+)/wordpress", UserWordpressAPIHandler),
    (r"/api/users/([^/]+)/fieldtrip", UserFieldtripAPIHandler),
]
