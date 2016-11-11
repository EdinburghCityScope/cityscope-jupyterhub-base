from tornado import web, gen

from .. import orm
from ..utils import admin_only, url_path_join
from .base import BaseHandler
from .login import LoginHandler
import os, uuid, re

__UPLOADS__ = os.path.expanduser('~') + "/uploads/"


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
        file_uploaded = False
        message = ''
        error_message = ''
        message_class = ''
        form_class = ''

        if len(self.request.files) != 0:
            message = '<h3>Summary</h3>'
            fileinfo = self.request.files['filearg'][0]
            fname = fileinfo['filename']
            filename, file_extension = os.path.splitext(fname)
            newname = (re.sub('[^\w\s-]', '', filename).strip().lower())
            newname = (re.sub('[-\s]+', '-', newname))
            cname = newname + file_extension
            fh = open(__UPLOADS__ + cname, 'wb')
            fh.write(fileinfo['body'])
            messages = cname + " was successfully uploaded to " + __UPLOADS__ + cname +". Info is {}".format(message)
            message_class = 'bg-success'
        else:
            messages = 'Oops, there was a problem...'
            error_message = 'You forgot to select a file'
            message_class = 'bg-danger'
            form_class = 'has-error'

        html = self.render_template('fileupload.html',
        user=self.get_current_user(),
        messages = messages,
        error_message = error_message,
        message_class = message_class,
        form_class = form_class
        )
        self.finish(html)

class HelloHandler(BaseHandler):
    def get(self):
        user = self.get_current_user()
        userhome = os.path.expanduser('~')
        self.write("Hello {0}. Your home is {1}".format(user.name,userhome))


default_handlers = [
    (r'/hello', HelloHandler),
    (r'/add-dataset',DataImportHandler),
]
