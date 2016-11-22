from tornado import web, gen

from .. import orm
from ..utils import admin_only, url_path_join
from .base import BaseHandler
from .login import LoginHandler
import os, re, unicodedata, csv, sys, time

__UPLOADS__ = os.path.expanduser('~') + "/datasets/"
_MAXFILESIZE = 50 * 1024 * 1024 # 50mb
# make sure the directory exists
if not os.path.exists(__UPLOADS__):
    try:
        os.makedirs(__UPLOADS__)
    except Exception as e:
        #error_message.append('Unable to create directory: {0}'.format(__UPLOADS__))
        raise RuntimeError('Unable to create dataset storage directory: {0}'.format(e))


class DataImportHandler(BaseHandler):
    """Render the add-dataset form"""
    def initialize(self, messages = [], message_class = '', error_message = [], form_class = '', delete_file = False, file_uploaded = False):
        self.messages = messages
        self.message_class = message_class
        self.error_message = error_message
        self.form_class = form_class
        self.delete_file = delete_file
        self.file_uploaded = file_uploaded

    ###############################
    #######  main  methods  #######
    ###############################
    @web.authenticated
    def get(self):
        self.initialize()
        self.render_page()


    @gen.coroutine
    def post(self):
        self.initialize(messages = [], message_class = '', error_message = [], form_class = '', delete_file = False, file_uploaded = False)
        # do we have a file?
        if len(self.request.files) != 0:
            fileinfo = self.request.files['filearg'][0]
            savedpath = self.save_file(fileinfo)
            self.check_file_size(savedpath)
            self.validate_file(savedpath)
            if self.delete_file is True:
                self.remove_file(savedpath)

        else:
            self.error_message.append('You forgot to select a file')

        self.set_messages_classes();
        self.render_page()


    ###############################
    #######  Local methods  #######
    ###############################
    def validate_file(self,savedpath):
        if self.file_uploaded is True:
            try:
                csvfile = open(savedpath, newline='')
                file_content = csvfile.readline().strip(" ") + csvfile.readline().strip(" ")
                if len(file_content) == 0:
                    self.error_message.append('file is empty')
                    self.delete_file = True
            except Exception as err:
                self.error_message.append('Could not read file: {0}'.format(err))
                file_content = ''

            try:
                header = csv.Sniffer().has_header(file_content)
            except Exception as err:
                self.error_message.append('Could not determine header: {0}'.format(err))
                self.delete_file = True
                header = False

            if header is False:
                self.error_message.append("Unable to read/find header row. Please add a header row to your csv file and re-upload.")
                self.delete_file = True
                messages = []

            csvfile.close()


    def check_file_size(self,savedpath):
        if self.file_uploaded is True:
            filesize = os.path.getsize(savedpath)
            if (filesize > _MAXFILESIZE):
                self.error_message.append("File too large: Uploaded datasets should smaller than 50mb.")
                self.delete_file = True
                self.messages = []


    def remove_file(self,savedpath):
            try:
                os.remove(savedpath)
            except:
                self.error_message.append('Validation failed. Unable to delete file {0}. This has all gone wrong.'.format(fname))


    def set_messages_classes(self):
        if len(self.error_message):
            self.messages.append('Something went wrong.')
            self.file_uploaded = False
            self.message_class = 'bg-danger'
            self.form_class = 'has-error'
        else:
            self.file_uploaded = True
            self.message_class = 'bg-success'
            self.messages.append("File upload successful.")


    def render_page(self):
        html = self.render_template('fileupload.html',
        user=self.get_current_user(),
        messages = self.messages,
        error_message = self.error_message,
        message_class = self.message_class,
        form_class = self.form_class,
        uploaded = self.file_uploaded,
        datasets = list_datasets(),
        )
        self.finish(html)


    def save_file(self,fileinfo):
        fname = fileinfo['filename']
        filename, file_extension = os.path.splitext(fname)

        if (file_extension.lower() != '.csv'):
            self.error_message.append('Only csv files are accepted')
        # make your file name a nice ascii formatted string.
        newname = stringFormat(filename)
        if (newname == ''): # if there are no ascii characters, name the file after the user.
            user = self.get_current_user()
            newname = user.name
        cname = newname + file_extension
        if (newname != filename): # let the user know if the file was renamed
            self.messages.append('Your file was renamed from {0} to {1}'.format(fname,cname))

        # save the file to the users home directory.
        savedpath =  __UPLOADS__ + cname

        try:
            fh = open(savedpath, 'wb')
            fh.write(fileinfo['body'])
            fh.close()
            self.file_uploaded = True
        except Exception as err:
            self.error_message.append('Unable to upload file {0}. Reason was:{1}'.format(fname, err))
            self.messages = []
            self.file_uploaded = False

        return savedpath




class HelloHandler(BaseHandler):

    def get(self):
        user = self.get_current_user()
        userhome = os.path.expanduser('~')
        self.write("Hello {0}. Your home is {1}".format(user.name,userhome))
        msg = []
        err_msg = []
        original_name = '_Antonín_Dvořák_QA-(*)_(^!~#\'-"?=9  bcà@HéÉç_-'
        originalFile = original_name + '.csv'
        #filename = re.sub('[^0-9a-zA-Z+_. ]+', '_', original_name)
        filename = stringFormat(original_name)
        #filename = stringFormat(original_name)
        cname = filename + '.csv'
        msg.append("New string: {0}, was: {1}".format(cname,originalFile))

        temp_file = __UPLOADS__ + 'test.csv'
        if os.path.isfile(temp_file):
            csvfile = open(temp_file, newline='')
            firstline = csvfile.readline()
            #filecontent = csvfile.read()
            samplecontent = firstline + csvfile.readline()

            msg.append('opened {0}'.format(temp_file))
            msg.append('firstline is: {0}'.format(firstline))
            msg.append('samplecontent is: {0}'.format(samplecontent))

            try:
                dialect = csv.Sniffer().sniff(samplecontent)
                msg.append('dialect delimiter = {0}'.format(dialect.delimiter))
            except Exception as err:
                err_msg.append('Could not determine dialect: {0}'.format(err))
            print(dialect)
            try:
                header = csv.Sniffer().has_header(samplecontent)
                msg.append('header exists = {0}'.format(header))
            except Exception as err:
                err_msg.append('Could not determine header: {0}'.format(err))
            print(header)

            # close the file
            csvfile.close()


        if len(msg):
            self.write("Messages:")
            for message in msg:
                self.write("{0}<br/>".format(message))
        if len(err_msg):
            self.write("Errors:")
            for e in err_msg:
                self.write("{0}<br/>".format(e))

        dataset_dir = __UPLOADS__
        self.write("<p>Current files in: {0}<br/>".format(dataset_dir))

        file_list = os.listdir(dataset_dir)
        self.write("<ol>")
        for fname in file_list:
            local_file = dataset_dir + fname
            modified    = os.path.getmtime(local_file)
            self.write("<li>{0} ({1})</li>".format(fname, time.ctime(modified)))
        self.write("</ol>")


def list_datasets():
    dataset_dir = __UPLOADS__
    file_list = os.listdir(dataset_dir)
    datasets = []
    for fname in file_list:
        local_file = dataset_dir + fname
        modified    = os.path.getmtime(local_file)
        datasets.append({'file_name':fname, 'last_modified':time.ctime(modified)})

    return datasets


def stringFormat(string_arg):
    # return a string that only has alphanumeric and underscores
    nkfd_form = unicodedata.normalize('NFKD', string_arg)
    new_string = u''.join([c for c in nkfd_form if not unicodedata.combining(c)])
    return  re.sub('[^a-zA-Z_0-9+_+-.]+', '', new_string.lower()).strip("-_")


default_handlers = [
    (r'/hello', HelloHandler),
    (r'/add-dataset',DataImportHandler),
]
