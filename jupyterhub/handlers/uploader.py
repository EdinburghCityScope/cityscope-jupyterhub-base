from tornado import web, gen

from .. import orm
from ..utils import admin_only, url_path_join
from .base import BaseHandler
from .login import LoginHandler
import os, re, unicodedata, csv, sys, time, datetime, getpass, shutil, json, magic
from slugify import slugify

__UPLOADS__ = os.path.expanduser('~') + "/datasets/"
_MAXFILESIZE = 50 * 1024 * 1024 # 50mb

######################################
####### helper functions #############
######################################
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

def list_data_files(dataset_dir):
    '''lists uploaded file details from the
    /home/{user}/datasets/{dataset_name}/data/ directory.
    '''
    dataset_files_dir = dataset_dir + 'data/'
    dataset_files = [f for f in os.listdir(dataset_files_dir) if os.path.isfile(os.path.join(dataset_files_dir, f))]

    datafiles = []
    for data_file in dataset_files:
        filename, file_extension = os.path.splitext(data_file)
        file_extension = file_extension.lower()
        fullpath = dataset_files_dir + data_file
        modified = os.path.getmtime(fullpath)
        mime_type = get_mime_type(file_extension=file_extension,fullpath=fullpath)
        datafiles.append({
            'file_name':data_file,
            'file_id':filename.lower() + file_extension.lower().replace('.', '_'),
            'filetype':file_extension.lower(),
            'mimetype':mime_type,
            'last_modified':time.ctime(modified),
        })
    return datafiles

def get_mime_type(file_extension, fullpath):
    mime_type = None
    x = file_extension
    if x == '.csv':
        mime_type = 'text/csv'
    elif x == '.json':
        mime_type = 'application/json'
    elif x == '.js':
        mime_type = 'application/javascript'
    elif x == '.geojson':
        mime_type = 'application/vnd.geo+json'
    elif x == '.txt' or x == '.text':
        mime_type = 'text/plain'
    elif x == '.pdf':
        mime_type = 'application/pdf'
    elif x == '.doc' or x == '.docx':
        mime_type = 'application/msword'
    elif x == '.rtf' or x == '.rt':
        mime_type = 'application/rtf'
    elif x == '.xml':
        mime_type = 'text/xml'
    elif x == '.htm' or x == '.html':
        mime_type = 'text/html'
    elif x == '.py':
        mime_type = 'text/x-script.python'

    if mime_type == None:
        mime = magic.Magic(mime=True)
        mime_type = mime.from_file(fullpath)

    return mime_type

def format_string(string_arg):
    return slugify(string_arg)

def get_uploads_dir():
    # make sure the uploads directory exists
    if not os.path.isdir(__UPLOADS__):
        try:
            os.makedirs(__UPLOADS__)
        except Exception as e:
            raise RuntimeError('Unable to create upload storage directory: {0}'.format(e))
    return __UPLOADS__

def get_dataset_dir(dataset_name):
    '''gets the file path of a dataset by dataset name and user path'''
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

def python_to_json(object):
    return object.__dict__

def json_date_today():
    return json.dumps(datetime.datetime.now().strftime('%Y-%m-%d'))

def read_json_file(fullpath):
    d=''
    if os.path.isfile(fullpath):
        try:
            with open(fullpath) as json_data:
                d = json.load(json_data)
                json_data.close()
        except Exception as err:
            d = ''
    return d

def get_dcat_distribution_object(title='', description='', mediaType='', downloadURL='', license='',):
    ''' description of each /data file in a dataset
        download url will be in the format:
        https://github.com/EdinburghCityScope/{uun}/cec-litter-bins/raw/master/data/litter-bins.csv
        which redirects to:
        https://raw.githubusercontent.com/EdinburghCityScope/{uun}/cec-litter-bins/master/data/litter-bins.csv

    '''
    return {
            'title': title,
            'description' : description,
            'mediaType' : mediaType,
            'downloadURL' : downloadURL,
            'license' : license
        }


######################################
########### main classes #############
######################################


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
    def initialize(self, messages = [], message_class = '', error_message = [], form_class = '', slug='', form_fields=None):
        self.messages = messages
        self.message_class = message_class
        self.error_message = error_message
        self.form_class = form_class
        self.slug = slug
        self.form_fields = form_fields
        dcat = DCAT(dataset_name = self.slug)
        self.dcat_data = dcat.get_dcat_file()
        self.form_fields = self.get_dcat_form()


    ###############################
    #######  main  methods  #######
    ###############################
    @web.authenticated
    def get(self, slug):
        self.initialize(slug=slug)
        self.render_page()

    @gen.coroutine
    def post(self, slug):
        ''' # if the form has been posted:
            # http://www.tornadoweb.org/en/stable/guide/structure.html?highlight=form%20input
            # Request data in the formats used by HTML forms will be parsed
            # for you and is made available in methods like
            # get_query_argument and get_body_argument
            # eg form.title will be: self.get_body_argument("title")
        '''
        self.initialize(slug=slug)
        print("handling form post")
        self.validate_form()
        self.render_page()

    def validate_form(self):
        # clear any messages
        self.messages = []
        # check standard input:
        standard_fields = ['title','description','language','publisher','email','keywords']
        for field in standard_fields:
            if self.form_fields[field]['required'] == True and self.form_fields[field]['value'] == '':
                self.form_fields[field]['css_class'] = 'has-error'
                self.messages.append(self.form_fields[field]['error_text'])
            else:
                self.form_fields[field]['css_class'] = ''

        for field in self.form_fields['distribution']:
            #this will give us a dictionary for EACH file which has three inputs:
            inputs = ['title','description','license']
            # each input has a form name
            for form_input_name in inputs:
                fieldname = field[form_input_name]['name']
                if field[form_input_name]['required'] == True and field[form_input_name]['value'] == '':
                    field[form_input_name]['css_class'] = 'has-error'
                    self.messages.append(field[form_input_name]['error_text'])
                else:
                    field[form_input_name]['css_class'] = ''

    def get_dcat_form(self):
        ''' form inputs need to be generated dynamically as we don't know
            which data files exist in each dataset.
            It would be nice to have these generated so we can loop through them.
            each file should have a title, description and license.
                title='',
                description='',
                language=['en'],
                publisher = {'name':'','mbox':''}, # dictionary
                keyword=[],
                distribution=[]
        '''
        distribution = []
        datafiles = list_data_files(get_dataset_dir(self.slug))
        for datafile in datafiles:
            file_name = datafile['file_name']
            distribution_title = datafile['file_id'] + '[title]'
            title_value = self.get_distribution_field_value(field_name='title',file_name=file_name,input_name=distribution_title)
            distribution_description = datafile['file_id'] + '[description]'
            description_value = self.get_distribution_field_value(field_name='description',file_name=file_name,input_name=distribution_description)
            distribution_license = datafile['file_id'] + '[license]'
            license_value = self.get_distribution_field_value(field_name='license',file_name=file_name,input_name=distribution_license)

            distribution.append(
                {
                'file_name':file_name,'mimetype':datafile['mimetype'],
                'title':{
                        'name':distribution_title,
                        'required':True,
                        'css_class':'',
                        'value':title_value,
                        'error_text': 'Please provide a title for the file: {0}'.format(file_name)
                        },
                'description':{
                        'name':distribution_description ,
                        'required':True,
                        'css_class':'',
                        'value':description_value,
                        'error_text': 'Please provide a description for the file: {0}'.format(file_name)
                        },
                'license':{
                        'name':distribution_license ,
                        'required':True,
                        'css_class':'',
                        'value':license_value,
                        'error_text': 'Please provide a license type for the file: {0}'.format(file_name)
                        },
                }
            )
        form_inputs = {
            'title':{
                    'required':True,
                    'css_class':'',
                    'value':self.get_form_value('title'),
                    'help_text':'',
                    'error_text': 'Please provide a title for your dataset}'
                    },
            'description':{
                    'required':True,
                    'css_class':'',
                    'value':self.get_form_value('description'),
                    'help_text':'',
                    'error_text': 'Please provide a description for your dataset}'
                    },
            'language':{
                    'required':True,
                    'css_class':'',
                    'value':self.get_form_value('language'),
                    'help_text':'',
                    'error_text': 'Please provide a language code for your dataset}'
                    }, #https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
            'publisher':{
                    'required':True,
                    'css_class':'',
                    'value':self.get_form_value('publisher'),
                    'help_text':'',
                    'error_text': 'Who is the publisher this dataset}',
                    },
            'email':{
                    'required':True,
                    'css_class':'',
                    'value':self.get_form_value('email'),
                    'help_text':'',
                    'error_text': 'Please provide an email address for the publisher of this dataset}'},
            'keywords':{
                    'required':False,
                    'css_class':'',
                    'value':self.get_form_value('keywords'),
                    'help_text':'A comma delimited list of words',
                    'error_text': 'Please provide some keywords that describe your dataset}'},
             # distribution inputs should ALWAYS be linked to the physical file system not the data.json file.
            'distribution':distribution
            }
        return form_inputs

    def get_distribution_field_value(self,field_name,file_name,input_name):

        the_value = self.get_body_argument(input_name, default=None, strip=True)
        #print('the value for {0}] was:{1}'.format(input_name,the_value))
        if the_value == None:
            try:
                distribution_data = self.dcat_data['distribution']
            except:
                distribution_data = get_dcat_distribution_object()
            for file_details in distribution_data:
                try:
                    file_url = file_details['downloadURL']
                    split_url = file_url.split("/")
                    data_file_name = split_url[-1]
                    if data_file_name == file_name:
                        the_value = file_details[field_name]

                except:
                    the_value = ''
        if the_value == None:
            the_value = ''
        #print('the value for {0}] IS NOW :{1}'.format(input_name,the_value))
        return the_value

    def get_form_value(self,input_name):

        the_value = self.get_body_argument(input_name, default=None, strip=True)

        if the_value == None:
            try:
                if input_name == 'keywords':
                    keyword_list = self.dcat_data['keyword']
                    the_value = ','.join(keyword_list)
                elif input_name == 'publisher':
                    the_value = self.dcat_data['publisher']['name']
                elif input_name == 'email':
                    the_value = self.dcat_data['publisher']['mbox']
                else:
                    the_value = self.dcat_data[input_name]
            except:
                    the_value = ''
        if the_value == None:
            the_value = ''
        #print('the value for [{0}] was:{1}'.format(input_name,the_value))
        return the_value

    def render_page(self):
        if len(self.messages) > 0:
            self.message_class = 'bg-danger'
            successful = False
        else:
            self.message_class = 'bg-success'
            successful = True
            self.messages.append('Thank you. Validation successful.')

        html = self.render_template('publish_dataset.html',
        user = get_user_uun(),
        messages = self.messages,
        error_message = self.error_message,
        message_class = self.message_class,
        successful = successful,
        form_class = self.form_class,
        dataset_name = self.slug,
        datafiles = list_data_files(get_dataset_dir(self.slug)),
        form_fields = self.form_fields
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


class DCAT:
    '''This returns a python readable object of a dcat.json file within a dataset.
       The dataset_dir argument is the path to the dataset.
    '''
    def __init__(   self,
                    dataset_dir='',
                    dataset_name='',
                    id='',
                    title='',
                    description='',
                    issued='',
                    modified=json_date_today(),
                    language=['en'],
                    publisher = {'name':'','mbox':''}, # dictionary
                    spatial='http://www.geonames.org/maps/google_55.95_-3.193.html',
                    keyword=[],
                    distribution=[], # list of dictionary objects
                    ):
        self.dataset_dir = dataset_dir
        self.dataset_name = dataset_name
        self.id = id #id='https://github.com/EdinburghCityScope/{uun}/{dataset_name}',
        self.title = title
        self.description = description
        self.issued = issued
        self.modified = modified
        self.language = language
        self.publisher = publisher
        self.spatial = spatial
        self.keyword = keyword
        self.distribution = distribution

        if self.dataset_dir == '' and self.dataset_name != '':
            self.dataset_dir = get_dataset_dir(self.dataset_name)

        if self.dataset_dir != '' and self.dataset_name == '':
            dirs = self.dataset_dir.split("/")
            self.dataset_name = dirs[-2] #this should give us the dataset_name from /home/{uun}/datasets/{dataset_name}/

        # self.variables
        self.data_path = self.dataset_dir + 'data/'
        self.dcat_file_path = self.dataset_dir + 'data.json'

        #print(python_to_json(self))
        if os.path.isdir(self.data_path):
            print('we have a valid dataset_dir: {0}'.format(self.data_path))


    def get_dcat_file(self):
        '''reads (or creates) a dcat.json file into a Python object based on a supplied file path'''
        print('getting dcat file')
        if os.path.isfile(self.dcat_file_path):
            data = read_json_file(self.dcat_file_path)
            #print('Data read from {0} file: {1}'.format(self.dcat_file_path,data))
        else:
            data = python_to_json(self)
            #do something
        return data

    def read_dcat_file(self):
        print('reading dcat file')

    def write_dcat_file(self):
        print('writing dcat file')


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

        dcat_dir = dataset_dir + 'abc/'
        dcat_data = DCAT(dcat_dir)
        #print(dcat_data)
        self.write("<p>dCat file is: {}</p>".format(dcat_data.get_dcat_file()))


default_handlers = [
    (r'/hello', HelloHandler),
    (r'/add-dataset',DataImportHandler),
    (r"/delete-dataset/([^/]+)", DeleteDatasetHandler),
    (r"/confirm-delete/([^/]+)", ConfirmDeleteDatasetHandler),
    (r"/publish-dataset/([^/]+)", PublishDatasetHandler),
]
