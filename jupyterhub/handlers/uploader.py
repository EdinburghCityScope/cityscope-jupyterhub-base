from tornado import web, gen

from .. import orm
from ..utils import admin_only, url_path_join
from .base import BaseHandler
from .login import LoginHandler
import os, re, unicodedata, csv, sys, time, datetime, getpass, shutil, json
from slugify import slugify

__UPLOADS__ = os.path.expanduser('~') + "/datasets/"
_MAXFILESIZE = 50 * 1024 * 1024 # 50mb


class DataImportHandler(BaseHandler):
    """Render the add-dataset form"""
    def initialize(self, messages = [], message_class = '', error_message = [], form_class = '', delete_file = False, file_uploaded = False, slug=''):
        self.messages = messages
        self.message_class = message_class
        self.error_message = error_message
        self.form_class = form_class
        self.delete_file = delete_file
        self.file_uploaded = file_uploaded
        self.template = 'fileupload.html'
        self.slug = slug

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
                self.remove_file(self.slug)

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


    def remove_file(self,slug):
        savedpath = get_dataset_dir(slug)
        try:
            #os.remove(savedpath)
            shutil.rmtree(savedpath)
        except:
            self.error_message.append('Validation failed. Unable to delete dataset {0}. This has all gone wrong.'.format(savedpath))


    def set_messages_classes(self):
        if len(self.error_message):
            self.messages.append('Something went wrong.')
            self.file_uploaded = False
            self.message_class = 'bg-danger'
            self.form_class = 'has-error'
            self.template = 'fileupload.html'
        else:
            self.file_uploaded = True
            self.message_class = 'bg-success'
            self.messages.append("File upload successful.")
            self.template = 'fileupload.html'


    def render_page(self):
        html = self.render_template(self.template,
        user = get_user_uun(),
        messages = self.messages,
        error_message = self.error_message,
        message_class = self.message_class,
        form_class = self.form_class,
        successful = self.file_uploaded,
        datasets = list_datasets(),
        )
        self.finish(html)


    def save_file(self,fileinfo):
        fname = fileinfo['filename']
        filename, file_extension = os.path.splitext(fname)
        #print(fileinfo)
        if (fileinfo['content_type'].lower() != 'text/csv') or (file_extension.lower() != '.csv'):
            self.error_message.append('Only csv files are accepted.')
            self.delete_file = True

        # make your file name a nice ascii formatted string.
        newname = format_string(filename)
        if (newname == ''): # if there are no ascii characters, name the file after the user.
            newname = get_user_uun()
        self.slug = newname
        cname = newname + file_extension
        if (newname != filename): # let the user know if the file was renamed
            self.messages.append('Your file was renamed from {0} to {1}'.format(fname,cname))

        # save the file to the users home directory.
        saved_dir_path = get_dataset_dir(newname)
        saved_file_path =  saved_dir_path + 'data/' + cname

        try:
            fh = open(saved_file_path, 'wb')
            fh.write(fileinfo['body'])
            fh.close()
            self.file_uploaded = True
        except Exception as err:
            self.error_message.append('Unable to upload file {0}. Reason was:{1}'.format(fname, err))
            self.messages = []
            self.file_uploaded = False

        return saved_file_path


class PublishDatasetHandler(BaseHandler):
    def initialize(self, messages = [], message_class = '', error_message = [], form_class = '', slug=''):
        self.messages = messages
        self.message_class = message_class
        self.error_message = error_message
        self.form_class = form_class
        self.slug = slug

    ###############################
    #######  main  methods  #######
    ###############################
    @web.authenticated
    def get(self, slug):
        self.initialize(slug=slug)
        self.render_page()

    @gen.coroutine
    def post(self):
        print(form)
        self.initialize(slug=slug)
        self.render_page()

    def render_page(self):
        html = self.render_template('publish_dataset.html',
        user = get_user_uun(),
        messages = self.messages,
        error_message = self.error_message,
        message_class = self.message_class,
        form_class = self.form_class,
        dataset_name = self.slug,
        datafiles = list_data_files(self.slug)
        )
        self.finish(html)


class ConfirmDeleteDatasetHandler(BaseHandler):
    @web.authenticated
    def get(self, slug):
        if not slug: raise tornado.web.HTTPError(404)
        dataset_name = slug
        html = self.render_template('confirm_delete.html', dataset_name = dataset_name,)
        self.finish(html)


class DeleteDatasetHandler(BaseHandler):
    @web.authenticated
    def get(self, slug):
        self.messages = []
        self.message_class = ''
        self.file_deleted = False

        if not slug: raise tornado.web.HTTPError(404)

        savedpath = get_dataset_dir(slug)
        if os.path.isdir(savedpath):
            try:
                #os.remove(savedpath)
                shutil.rmtree(savedpath)
                self.file_deleted = True
            except Exception as err:
                self.messages.append("Oops - Could not delete dataset: {0}. Error: {1}</p>".format(slug,err))
        else:
            self.messages.append("Oops - Could not dataset: {0}".format(slug))

        if self.file_deleted == True:
            self.messages.append("Dataset: {0} deleted".format(slug))
            self.message_class = 'bg-success'
        else:
            self.message_class = 'bg-danger'

        self.render_page()

    def render_page(self):
        html = self.render_template('fileupload.html',
        successful = self.file_deleted,
        messages = self.messages,
        message_class = self.message_class,
        datasets = list_datasets(),
        )
        self.finish(html)


def get_user_tree():
    # /user/{{user.name}}/tree/datasets/{{fname}}
    return '/user/' + get_user_uun() + '/tree/datasets/'


def get_user_uun():
    return getpass.getuser()


def list_datasets():
    dataset_dir = get_uploads_dir()
    dir_names = os.listdir(dataset_dir)

    datasets = []
    for dir_name in dir_names:
        fullpath = dataset_dir + dir_name
        if os.path.isdir(fullpath):
            modified    = os.path.getmtime(fullpath)
            user_tree = get_user_tree() + dir_name + '/'
            datasets.append({'file_name':dir_name, 'last_modified':time.ctime(modified), 'file_link':user_tree})
    return datasets


def list_data_files(dataset_name):
    '''lists uploaded file details from the
    /home/{user}/datasets/{dataset_name}/data/ directory.
    '''
    dataset_files_dir = get_dataset_dir(dataset_name) + 'data/'
    dataset_files = [f for f in os.listdir(dataset_files_dir) if os.path.isfile(os.path.join(dataset_files_dir, f))]

    datafiles = []
    for data_file in dataset_files:
        filename, file_extension = os.path.splitext(data_file)
        fullpath = dataset_files_dir + data_file
        modified = os.path.getmtime(fullpath)
        datafiles.append({
            'file_name':data_file,
            'file_id':filename.lower() + '_' + file_extension.lower(),
            'filetype':file_extension.lower(),
            'last_modified':time.ctime(modified),
        })
    return datafiles


def get_data_file_form_inputs(dataset_name):
    '''form inputs need to be generated dynamically as we don't know
    which data files exist in each dataset.
    It would be nice to have these generated so we can loop through them.
    each file should have a title, description and license.
    '''
    form_inputs = []
    if not dataset_name:
        return form_inputs #error should be captured by calling page
    else:
        datafiles = list_data_files(dataset_name)


def format_string(string_arg):
    return slugify(string_arg)
    # return a string that only has alphanumeric or hyphens
    #string_arg = string_arg.replace(" ","-")
    #string_arg = string_arg.replace("_","-")
    #nkfd_form = unicodedata.normalize('NFKD', string_arg)
    #new_string = u''.join([c for c in nkfd_form if not unicodedata.combining(c)])
    #new_string = re.sub('[^a-zA-Z_0-9+_+-.]+', '', new_string.lower()).strip("-_")
    #new_string = re.sub('-+','-',new_string)
    #return  new_string


def get_uploads_dir():
    # make sure the uploads directory exists
    if not os.path.isdir(__UPLOADS__):
        try:
            os.makedirs(__UPLOADS__)
        except Exception as e:
            raise RuntimeError('Unable to create upload storage directory: {0}'.format(e))
    return __UPLOADS__


def get_dataset_dir(dataset_name):
    # does the dataset_name dir exist?
    dataset_dir = get_uploads_dir() + dataset_name + '/'
    if not os.path.isdir(dataset_dir):
        try:
            os.makedirs(dataset_dir)
        except Exception as e:
            raise RuntimeError('Unable to create dataset storage directory: {0}'.format(e))

    # is there a the data directory under the dataset_dir folder?
    data_dir = dataset_dir + 'data' + '/'
    if not os.path.isdir(data_dir):
        try:
            os.makedirs(data_dir)
        except Exception as e:
            raise RuntimeError('Unable to create data storage directory: {0}'.format(e))

    return dataset_dir

def json_default(object):
    return object.__dict__

def json_date_today():
    return json.dumps(datetime.datetime.now().strftime('%Y-%m-%d'))

def get_dcat_distribution_object(title='', description='', mediaType='', downloadURL='', license='',):
    ''' description of each /data file in a dataset'''
    return {
            'title': title,
            'description' : description,
            'mediaType' : mediaType,
            'downloadURL' : downloadURL,
            'license' : license
        }


class DCAT:
    '''This returns a python readable object of a dcat.json file within a dataset.
       The dataset_dir argument is the path to the dataset.
    '''
    def __init__(   self,
                    dataset_dir='',
                    dataset_name='',
                    id='https://github.com/EdinburghCityScope/',
                    title='',
                    description='',
                    issued=json_date_today(),
                    modified=json_date_today(),
                    language=['en'],
                    publisher = {'name':'','mbox':''}, # dictionary
                    spatial='http://www.geonames.org/maps/google_55.95_-3.193.html',
                    keyword=[],
                    distribution=[get_dcat_distribution_object()], # list of dictionary objects
                    ):
        self.dataset_dir = dataset_dir
        self.dataset_name = dataset_name
        self.id = id
        self.title = title
        self.description = description
        self.issued = issued
        self.modified = modified
        self.language = language
        self.publisher = publisher
        self.spatial = spatial
        self.keyword = keyword
        self.distribution = distribution
        print(json_default(self))
        #return json_default(self)


        if dataset_dir != '':
            dirs = dataset_dir.split("/")
            self.dataset_name = dirs[-2]
            print('dataset_name = {}'.format(self.dataset_name))



class HelloHandler(BaseHandler):
    def get(self):
        msg = []
        err_msg = []
        original_name = '_Antonín_Dvořák_QA-(*)_(^!~#\'-"?=9  bcà@HéÉç_-Компьютер'
        originalFile = original_name + '.csv'
        #filename = re.sub('[^0-9a-zA-Z+_. ]+', '_', original_name)
        filename = format_string(original_name)
        cname = filename + '.csv'
        msg.append("<p>Renamed: <br/>{1} to: <br/> {0}</p>".format(cname,originalFile))

        if len(msg):
            self.write("Messages:")
            for message in msg:
                self.write("{0}<br/>".format(message))
        if len(err_msg):
            self.write("Errors:")
            for e in err_msg:
                self.write("{0}<br/>".format(e))

        dataset_dir = get_uploads_dir()
        self.write("<p>Current files in: {0}<br/>".format(dataset_dir))

        file_list = os.listdir(dataset_dir)
        self.write("<ol>")
        for fname in file_list:
            local_file = dataset_dir + fname
            modified    = os.path.getmtime(local_file)
            self.write("<li>{0} ({1})</li>".format(fname, time.ctime(modified)))
        self.write("</ol>")

        self.write("<p>datasets dir = {0}</p>".format(dataset_dir))

        self.write("<ol>")
        for dirname in file_list:
            fullpath = get_uploads_dir() + dirname
            if os.path.isdir(fullpath):
                self.write("<li>{0}</li>".format(dirname))
        self.write("</ol>")

        self.write("<p>Parent directory name is: {0}</p>".format(getpass.getuser()))

        dcat_dir = dataset_dir + 'test/'
        dcat_data = DCAT(dcat_dir)
        print(dcat_data)
        self.write("<p>dCat file is: {}</p>".format(json_default(dcat_data)))


default_handlers = [
    (r'/hello', HelloHandler),
    (r'/add-dataset',DataImportHandler),
    (r"/delete-dataset/([^/]+)", DeleteDatasetHandler),
    (r"/confirm-delete/([^/]+)", ConfirmDeleteDatasetHandler),
    (r"/publish-dataset/([^/]+)", PublishDatasetHandler),
]
