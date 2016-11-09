from tornado import web, gen

from .. import orm
from ..utils import admin_only, url_path_join
from .base import BaseHandler
from .login import LoginHandler
import os, uuid, re

__UPLOADS__ = "../uploads/"


class DataImportHandler(BaseHandler):
    """Render the add-dataset form"""
    @web.authenticated
    def get(self):
        html = self.render_template('fileupload.html',
            user=self.get_current_user(),
        )
        self.finish(html)

    @gen.coroutine
    def post(self):
        fileinfo = self.request.files['filearg'][0]
        print("fileinfo is {0}".format(fileinfo))
        fname = fileinfo['filename']
        filename, file_extension = os.path.splitext(fname)
        print("filename is {0}".format(filename))
        print("extn is {0}".format(file_extension))
        newname = (re.sub('[^\w\s-]', '', filename).strip().lower())
        newname = (re.sub('[-\s]+', '-', newname))
        cname = newname + file_extension
        print("cname is {0}".format(cname))
        fh = open(__UPLOADS__ + cname, 'wb')
        fh.write(fileinfo['body'])
        self.write(cname + " was successfully uploaded.")


class HelloHandler(BaseHandler):
    def get(self):
        user = self.get_current_user()
        self.write("Hello {0}".format(user.name))


default_handlers = [
    (r'/hello', HelloHandler),
    (r'/add-dataset',DataImportHandler),
]
