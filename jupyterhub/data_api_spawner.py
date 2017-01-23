"""Class for spawning single-user notebook servers."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import itertools
import errno
import os
import pipes
import pwd
import signal
import string
import sys
import grp
import tarfile
import base64
from textwrap import dedent
from concurrent.futures import ThreadPoolExecutor

from subprocess import Popen
from tempfile import mkdtemp

from tornado import gen
from tornado.ioloop import IOLoop, PeriodicCallback

from traitlets.config import LoggingConfigurable
from traitlets import (
    Any, Bool, Dict, Instance, Integer, Float, List, Unicode,
)

from pprint import pformat

from .traitlets import Command
from .utils import random_port
from .utils import recursive_format
from pprint import pformat

import docker
from docker.errors import APIError
from docker.utils import kwargs_from_env

from github import Github

from escapism import escape

class DataApiSpawner(LoggingConfigurable):
    user = Any()
    hub = Any()
    authenticator = Any()
    api_token = Unicode()
    ip = Unicode('127.0.0.1', config=True,
                 help="The IP address (or hostname) the data api server should listen on"
                 )
    start_timeout = Integer(60, config=True,
                            help="""Timeout (in seconds) before giving up on the spawner.

            This is the timeout for start to return, not the timeout for the server to respond.
            Callers of spawner.start will assume that startup has failed if it takes longer than this.
            start should return when the server process is started and its location is known.
            """
                            )

    http_timeout = Integer(
        30, config=True,
        help="""Timeout (in seconds) before giving up on a spawned HTTP server

            Once a server has successfully been spawned, this is the amount of time
            we wait before assuming that the server is unable to accept
            connections.
            """
    )

    poll_interval = Integer(30, config=True,
                            help="""Interval (in seconds) on which to poll the spawner."""
                            )
    _callbacks = List()
    _poll_callback = Any()

    debug = Bool(False, config=True,
                 help="Enable debug-logging of the data API server"
                 )

    env_keep = List([
        'PATH',
        'PYTHONPATH',
        'CONDA_ROOT',
        'CONDA_DEFAULT_ENV',
        'VIRTUAL_ENV',
        'LANG',
        'LC_ALL',
    ], config=True,
        help="Whitelist of environment variables for the subprocess to inherit"
    )
    env = Dict()

    github_api_token=Unicode('', config=True,
                 help="The token for accessing the github API"
                 )

    notebook_base_dir=Unicode('/Users/%U/cityscope/', config=True,
                 help="The base directory for jupyterhub notebooks"
                 )

    def _env_default(self):
        env = {}
        for key in self.env_keep:
            if key in os.environ:
                env[key] = os.environ[key]
        env['JPY_API_TOKEN'] = self.api_token
        return env

    cmd = Command(['node'], config=True,
                  help="""The command used for starting a data api server."""
                  )
    args = List(['../cityscope-loopback-docker'], config=True,
                help="""Extra arguments to be passed to the data api server"""
                )

    default_url = Unicode('', config=True,
                          help="""The default URL for the data api server.

            Can be used in conjunction with --notebook-dir=/ to enable
            full filesystem traversal, while preserving user's homedir as
            landing page for notebook

            `%U` will be expanded to the user's username
            """
                          )

    data_setup_args = List(['../cityscope-loopback-docker/cityscope-data-starter.js'], config=True,
                help="""Extra arguments to be passed for data setup. Value of %U will be expanded to the user's username"""
                )

    def __init__(self, **kwargs):
        super(DataApiSpawner, self).__init__(**kwargs)

    def get_state(self):
        """store the state

        A black box of extra state for custom spawners.
        Subclasses should call `super`.

        Returns
        -------

        state: dict
             a JSONable dict of state
        """
        state = {}
        return state

    def clear_state(self):
        """clear any state that should be cleared when the process stops

        State that should be preserved across server instances should not be cleared.

        Subclasses should call super, to ensure that state is properly cleared.
        """
        self.api_token = ''

    def get_env(self):
        """Return the environment we should use

        Default returns a copy of self.env.
        Use this to access the env in Spawner.start to allow extension in subclasses.
        """
        return self.env.copy()

    def get_args(self):
        """Return the arguments to be passed after self.cmd"""
        args = self.args
        args.append('loopback-custom-base-url=%s' % self.user.name)

        if self.debug:
            args.append('--debug')
        return args

    def get_data_setup_args(self):
        """Return the arguments to be passed after self.cmd"""
        replaced_args = []
        for arg in self.data_setup_args:
            arg = arg.replace("%U",self.user.name)
            print(arg)
            replaced_args.append(arg)
        if self.debug:
            replaced_args.append('--debug')
        return replaced_args

    @gen.coroutine
    def github_file_copies(self,repository):
        """Do notebook and CSV data copies from a repository"""
        raise NotImplementedError("Override in subclass. Must be a Tornado gen.coroutine.")

    @gen.coroutine
    def start(self):
        """Start the single-user process"""
        raise NotImplementedError("Override in subclass. Must be a Tornado gen.coroutine.")

    @gen.coroutine
    def stop(self, now=False):
        """Stop the single-user process"""
        raise NotImplementedError("Override in subclass. Must be a Tornado gen.coroutine.")

    @gen.coroutine
    def setup_data(self,data,now=False):
        """Setup data in the API"""
        raise NotImplementedError("Override in subclass. Must be a Tornado gen.coroutine")

    @gen.coroutine
    def poll(self):
        """Check if the single-user process is running

        return None if it is, an exit status (0 if unknown) if it is not.
        """
        raise NotImplementedError("Override in subclass. Must be a Tornado gen.coroutine.")

    def add_poll_callback(self, callback, *args, **kwargs):
        """add a callback to fire when the subprocess stops

        as noticed by periodic poll_and_notify()
        """
        if args or kwargs:
            cb = callback
            callback = lambda: cb(*args, **kwargs)
        self._callbacks.append(callback)

    def stop_polling(self):
        """stop the periodic poll"""
        if self._poll_callback:
            self._poll_callback.stop()
            self._poll_callback = None

    def start_polling(self):
        """Start polling periodically

        callbacks registered via `add_poll_callback` will fire
        if/when the process stops.

        Explicit termination via the stop method will not trigger the callbacks.
        """
        if self.poll_interval <= 0:
            self.log.debug("Not polling subprocess")
            return
        else:
            self.log.debug("Polling subprocess every %is", self.poll_interval)

        self.stop_polling()

        self._poll_callback = PeriodicCallback(
            self.poll_and_notify,
            1e3 * self.poll_interval
        )
        self._poll_callback.start()

    @gen.coroutine
    def poll_and_notify(self):
        """Used as a callback to periodically poll the process,
        and notify any watchers
        """
        status = yield self.poll()
        if status is None:
            # still running, nothing to do here
            return

        self.stop_polling()

        add_callback = IOLoop.current().add_callback
        for callback in self._callbacks:
            add_callback(callback)

    death_interval = Float(0.1)

    @gen.coroutine
    def wait_for_death(self, timeout=10):
        """wait for the process to die, up to timeout seconds"""
        loop = IOLoop.current()
        for i in range(int(timeout / self.death_interval)):
            status = yield self.poll()
            if status is not None:
                break
            else:
                yield gen.sleep(self.death_interval)

def _try_setcwd(path):
    """Try to set CWD, walking up and ultimately falling back to a temp dir"""
    while path != '/':
        try:
            os.chdir(path)
        except OSError as e:
            exc = e # break exception instance out of except scope
            print("Couldn't set CWD to %s (%s)" % (path, e), file=sys.stderr)
            path, _ = os.path.split(path)
        else:
            return
    print("Couldn't set CWD at all (%s), using temp dir" % exc, file=sys.stderr)
    td = mkdtemp()
    os.chdir(td)

class LocalLoopbackProcessSpawner(DataApiSpawner):
    """A Data API Spawner that just uses Popen to start local processes as users.

    This is the default Data API spawner for CityScope JupyterHub.
    """

    INTERRUPT_TIMEOUT = Integer(10, config=True,
        help="Seconds to wait for process to halt after SIGINT before proceeding to SIGTERM"
    )
    TERM_TIMEOUT = Integer(5, config=True,
        help="Seconds to wait for process to halt after SIGTERM before proceeding to SIGKILL"
    )
    KILL_TIMEOUT = Integer(5, config=True,
        help="Seconds to wait for process to halt after SIGKILL before giving up"
    )

    proc = Instance(Popen, allow_none=True)
    pid = Integer(0)

    def get_state(self):
        """add pid to state"""
        state = super(LocalLoopbackProcessSpawner, self).get_state()
        if self.pid:
            state['pid'] = self.pid
        return state

    def clear_state(self):
        """clear pid state"""
        super(LocalLoopbackProcessSpawner, self).clear_state()
        self.pid = 0

    def user_env(self, env):
        env['USER'] = self.user.name
        home = pwd.getpwnam(self.user.name).pw_dir
        shell = pwd.getpwnam(self.user.name).pw_shell
        # These will be empty if undefined,
        # in which case don't set the env:
        if home:
            env['HOME'] = home
        if shell:
            env['SHELL'] = shell
        return env

    def get_env(self):
        """Add user environment variables"""
        env = super().get_env()
        env = self.user_env(env)
        return env

    @gen.coroutine
    def github_file_copies(self,repository):
        """Do notebook and CSV data copies from a repository"""
        print("Getting info from:",repository)
        github = Github(login_or_token=self.github_api_token);
        repo = github.get_repo(repository)
        print("Getting notebooks")
        result = repo.get_git_tree("master?recursive=1")
        for treeElement in result.tree:
            if ((treeElement.type=="blob") and (treeElement.path.startswith("notebooks/") or treeElement.path.startswith("data/"))):
                print(treeElement.path)
                blob = repo.get_git_blob(treeElement.sha)
                filename = self.notebook_base_dir.replace("%U",self.user.name)+"/"+repo.name+"/"+treeElement.path
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                with open(filename, "wb") as f:
                    print("Writing :",filename)
                    f.write(base64.b64decode(blob.content))
                    f.closed

    @gen.coroutine
    def setup_data(self,data):
        """Import data into loopback"""

        for repository in data:
            print("repository",repository)
            cmd=[]
            env=self.get_env()
            cmd.extend(self.cmd)
            cmd.extend(self.get_data_setup_args())
            self.log.info("Setting up %s", ' '.join(pipes.quote(s) for s in cmd))
            self.proc = Popen(cmd, env=env,
                start_new_session=True, # don't forward signals
                )
            self.github_file_copies(repository)

    @gen.coroutine
    def start(self,credential):
        """Start the process"""

        cmd = []
        env = self.get_env()

        cmd.extend(self.cmd)
        cmd.extend(self.get_args())

        self.log.info("Spawning %s", ' '.join(pipes.quote(s) for s in cmd))
        self.proc = Popen(cmd, env=env,
            #preexec_fn=self.make_preexec_fn(self.user.name),
            start_new_session=True, # don't forward signals
        )
        self.pid = self.proc.pid

    @gen.coroutine
    def poll(self):
        """Poll the process"""
        # if we started the process, poll with Popen
        if self.proc is not None:
            status = self.proc.poll()
            if status is not None:
                # clear state if the process is done
                self.clear_state()
            return status

        # if we resumed from stored state,
        # we don't have the Popen handle anymore, so rely on self.pid

        if not self.pid:
            # no pid, not running
            self.clear_state()
            return 0

        # send signal 0 to check if PID exists
        # this doesn't work on Windows, but that's okay because we don't support Windows.
        alive = yield self._signal(0)
        if not alive:
            self.clear_state()
            return 0
        else:
            return None

    @gen.coroutine
    def _signal(self, sig):
        """simple implementation of signal, which we can use when we are using setuid (we are root)"""
        try:
            os.kill(self.pid, sig)
        except OSError as e:
            if e.errno == errno.ESRCH:
                return False # process is gone
            else:
                raise
        return True # process exists

    @gen.coroutine
    def stop(self, now=False):
        """stop the subprocess

        if `now`, skip waiting for clean shutdown
        """
        if not now:
            status = yield self.poll()
            if status is not None:
                return
            self.log.debug("Interrupting %i", self.pid)
            yield self._signal(signal.SIGINT)
            yield self.wait_for_death(self.INTERRUPT_TIMEOUT)

        # clean shutdown failed, use TERM
        status = yield self.poll()
        if status is not None:
            return
        self.log.debug("Terminating %i", self.pid)
        yield self._signal(signal.SIGTERM)
        yield self.wait_for_death(self.TERM_TIMEOUT)

        # TERM failed, use KILL
        status = yield self.poll()
        if status is not None:
            return
        self.log.debug("Killing %i", self.pid)
        yield self._signal(signal.SIGKILL)
        yield self.wait_for_death(self.KILL_TIMEOUT)

        status = yield self.poll()
        if status is None:
            # it all failed, zombie process
            self.log.warn("Process %i never died", self.pid)

class UnicodeOrFalse(Unicode):
    info_text = 'a unicode string or False'
    def validate(self, obj, value):
        if value is False:
            return value
        return super(UnicodeOrFalse, self).validate(obj, value)

class DockerProcessSpawner(DataApiSpawner):
    """A Docker Process Spawner that just uses Docker containers to spawn data apis for users.
    Ported from https://github.com/jupyterhub/dockerspawner.
    """

    _executor = None
    @property
    def executor(self):
        """single global executor"""
        cls = self.__class__
        if cls._executor is None:
            cls._executor = ThreadPoolExecutor(1)
        return cls._executor

    _client = None
    @property
    def client(self):
        """single global client instance"""
        cls = self.__class__
        if cls._client is None:
            if self.use_docker_client_env:
                kwargs = kwargs_from_env(
                    assert_hostname=self.tls_assert_hostname
                )
                client = docker.Client(version='auto', **kwargs)
            else:
                if self.tls:
                    tls_config = True
                elif self.tls_verify or self.tls_ca or self.tls_client:
                    tls_config = docker.tls.TLSConfig(
                        client_cert=self.tls_client,
                        ca_cert=self.tls_ca,
                        verify=self.tls_verify,
                        assert_hostname = self.tls_assert_hostname)
                else:
                    tls_config = None

                docker_host = os.environ.get('DOCKER_HOST', 'unix://var/run/docker.sock')
                client = docker.Client(base_url=docker_host, tls=tls_config, version='auto')
            cls._client = client
        return cls._client

    container_id = Unicode()
    container_ip = Unicode('127.0.0.1', config=True)
    container_image = Unicode("cityscope/cityscope-loopback", config=True)
    notebook_container_prefix = Unicode(
        "jupyter",
        config=True,
        help=dedent(
            """
            Prefix for notebook container names. The full notebook container name for a particular
            user will be <prefix>-<username>.
            """
        )
    )
    container_prefix = Unicode(
        "loopback",
        config=True,
        help=dedent(
            """
            Prefix for container names. The full container name for a particular
            user will be <prefix>-<username>.
            """
        )
    )

    volumes = Dict(
        config=True,
        help=dedent(
            """
            Map from host file/directory to container file/directory.
            Volumes specified here will be read/write in the container.
            If you use {username} in the host file / directory path, it will be
            replaced with the current user's name.
            """
        )
    )

    volume_driver = Unicode("convoy",
    config=True,
    help=dedent(
        """
        Volume driver to be used, defaults to convoy.
        """
    ))

    read_only_volumes = Dict(
        config=True,
        help=dedent(
            """
            Map from host file/directory to container file/directory.
            Volumes specified here will be read-only in the container.
            If you use {username} in the host file / directory path, it will be
            replaced with the current user's name.
            """
        )
    )

    use_docker_client_env = Bool(False, config=True, help="If True, will use Docker client env variable (boot2docker friendly)")
    tls = Bool(False, config=True, help="If True, connect to docker with --tls")
    tls_verify = Bool(False, config=True, help="If True, connect to docker with --tlsverify")
    tls_ca = Unicode("", config=True, help="Path to CA certificate for docker TLS")
    tls_cert = Unicode("", config=True, help="Path to client certificate for docker TLS")
    tls_key = Unicode("", config=True, help="Path to client key for docker TLS")
    tls_assert_hostname = UnicodeOrFalse(default_value=None, allow_none=True,
        config=True,
        help="If False, do not verify hostname of docker daemon",
    )

    remove_containers = Bool(False, config=True, help="If True, delete containers after they are stopped.")
    extra_create_kwargs = Dict(config=True, help="Additional args to pass for container create. {username} will be replaced with actual username")
    extra_start_kwargs = Dict(config=True, help="Additional args to pass for container start")
    extra_host_config = Dict(config=True, help="Additional args to create_host_config for container create")

    _container_safe_chars = set(string.ascii_letters + string.digits + '-')
    _container_escape_char = '_'

    hub_ip_connect = Unicode(
        "",
        config=True,
        help=dedent(
            """
            If set, DockerProcessSpawner will configure the containers to use
            the specified IP to connect the hub api.  This is useful
            when the hub_api is bound to listen on all ports or is
            running inside of a container.
            """
        )
    )

    use_internal_ip = Bool(
        False,
        config=True,
        help=dedent(
            """
            Enable the usage of the internal docker ip. This is useful if you are running
            jupyterhub (as a container) and the user containers within the same docker engine.
            E.g. by mounting the docker socket of the host into the jupyterhub container.
            """
        )
    )

    links = Dict(
        config=True,
        help=dedent(
            """
            Specify docker link mapping to add to the container, e.g.
                links = {'jupyterhub: 'jupyterhub'}
            If the Hub is running in a Docker container,
            this can simplify routing because all traffic will be using docker hostnames.
            """
        )
    )

    network_name = Unicode(
        "bridge",
        config=True,
        help=dedent(
            """
            The name of the docker network from which to retrieve the internal IP address. Defaults to the default
            docker network 'bridge'. You need to set this if you run your jupyterhub containers in a
            non-standard network. Only has an effect if use_internal_ip=True.
            """
        )
    )

    @property
    def tls_client(self):
        """A tuple consisting of the TLS client certificate and key if they
        have been provided, otherwise None.
        """
        if self.tls_cert and self.tls_key:
            return (self.tls_cert, self.tls_key)
        return None

    @property
    def volume_mount_points(self):
        """
        Volumes are declared in docker-py in two stages.  First, you declare
        all the locations where you're going to mount volumes when you call
        create_container.
        Returns a list of all the values in self.volumes or
        self.read_only_volumes.
        """
        return list(
            itertools.chain(
                self.volumes.values(),
                self.read_only_volumes.values(),
            )
        )

    @property
    def volume_binds(self):
        """
        The second half of declaring a volume with docker-py happens when you
        actually call start().  The required format is a dict of dicts that
        looks like:
        {
            host_location: {'bind': container_location, 'ro': True}
        }
        """
        volumes = {
            key.format(username=self.user.name): {'bind': value.format(username=self.user.name), 'ro': False}
            for key, value in self.volumes.items()
        }
        ro_volumes = {
            key.format(username=self.user.name): {'bind': value.format(username=self.user.name), 'ro': True}
            for key, value in self.read_only_volumes.items()
        }
        volumes.update(ro_volumes)
        return volumes

    _escaped_name = None
    @property
    def escaped_name(self):
        if self._escaped_name is None:
            self._escaped_name = escape(self.user.name,
                safe=self._container_safe_chars,
                escape_char=self._container_escape_char,
            )
        return self._escaped_name

    @property
    def notebook_container_name(self):
        return "{}-{}".format(self.notebook_container_prefix,self.escaped_name)

    @property
    def container_name(self):
        return "{}-{}".format(self.container_prefix, self.escaped_name)

    @gen.coroutine
    def get_state(self):
        state = super(DockerProcessSpawner, self).get_state()
        container = yield self.get_container()
        if container is None:
            self.log.info("Returning none")
            return None
        if container['State']['Running']:
            self.log.info("returning %s",container['Id'])
            state['container_id'] = container['Id']
            self.container_id = container['Id']
        else:
            state['container_state'] = container['State']['Status']
        return state

    def _public_hub_api_url(self):
        proto, path = self.hub.api_url.split('://', 1)
        ip, rest = path.split(':', 1)
        return '{proto}://{ip}:{rest}'.format(
            proto = proto,
            ip = self.hub_ip_connect,
            rest = rest
        )

    def _env_keep_default(self):
        """Don't inherit any env from the parent process"""
        return []

    def get_env(self):
        env = super(DockerProcessSpawner, self).get_env()
        env.update(dict(
            JPY_USER=self.user.name
        ))

        if self.hub_ip_connect:
           hub_api_url = self._public_hub_api_url()
        else:
           hub_api_url = self.hub.api_url
        env['JPY_HUB_API_URL'] = hub_api_url

        return env

    def _docker(self, method, *args, **kwargs):
        """wrapper for calling docker methods
        to be passed to ThreadPoolExecutor
        """
        m = getattr(self.client, method)
        return m(*args, **kwargs)

    def docker(self, method, *args, **kwargs):
        """Call a docker method in a background thread
        returns a Future
        """
        return self.executor.submit(self._docker, method, *args, **kwargs)

    @gen.coroutine
    def poll(self):
        """Check for my id in `docker ps`"""
        container = yield self.get_container()
        if not container:
            self.log.warn("container not found")
            return ""

        container_state = container['State']
        self.log.debug(
            "Container %s status: %s",
            self.container_id[:7],
            pformat(container_state),
        )

        if container_state["Running"]:
            return None
        else:
            return (
                "ExitCode={ExitCode}, "
                "Error='{Error}', "
                "FinishedAt={FinishedAt}".format(**container_state)
            )

    @gen.coroutine
    def get_container(self):
        self.log.debug("Getting container '%s'", self.container_name)
        try:
            container = yield self.docker(
                'inspect_container', self.container_name
            )
            self.container_id = container['Id']
        except APIError as e:
            if e.response.status_code == 404:
                self.log.info("Container '%s' is gone", self.container_name)
                container = None
                # my container is gone, forget my id
                self.container_id = ''
            elif e.response.status_code == 500:
                self.log.info("Container '%s' is on unhealthy node", self.container_name)
                container = None
                # my container is unhealthy, forget my id
                self.container_id = ''
            else:
                raise
        return container

    @gen.coroutine
    def github_file_copies(self,repository):
        """Do notebook and CSV data copies from a repository"""
        self.log.info("Getting info from: {0}".format(repository))

        github = Github(login_or_token=self.github_api_token);
        repo = github.get_repo(repository)
        self.log.info("Getting data")
        result = repo.get_git_tree("master?recursive=1")
        for treeElement in result.tree:
            if ((treeElement.type=="blob") and (treeElement.path.startswith("notebooks/") or treeElement.path.startswith("data/"))):
                self.log.info(treeElement.path)
                blob = repo.get_git_blob(treeElement.sha)
                filename = "/tmp/"+self.user.name+"/"+repo.name+"/"+treeElement.path
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                with open(filename, "wb") as f:
                    self.log.debug("Writing :",filename)
                    f.write(base64.b64decode(blob.content))
                    f.closed
        self.log.info("Creating tar file")
        tar = tarfile.open("/tmp/"+self.user.name+".tar","w")
        tar.add(arcname=os.path.basename(""), name="/tmp/"+self.user.name)
        tar.close()

        with open('/tmp/{user}.tar'.format(user = self.user.name), 'rb') as f:
            self.log.info("Sending tar to container: {container_name}".format(
                container_name = self.notebook_container_name)
            )
            yield self.docker('put_archive',
                container = self.notebook_container_name,
                path = '/tmp',
                data = f
            )

        self.log.info("Copying the repository to a temp directory")
        response = yield self.docker("exec_create",
            container = self.notebook_container_name,
            cmd = 'cp -r "/tmp/{repository}" "{notebook_dir}"'.format(
                repository = repo.name,
                notebook_dir = self.notebook_base_dir.replace("%U", self.user.name)
            ),
            user = '1000'
        )

        self.log.info("Moving the repository to the notebooks directory")
        yield self.docker('exec_start', response['Id'])

    @gen.coroutine
    def setup_data(self,data):
        """Import data into loopback"""
        for repository in data:

            dataUrl = "https://raw.githubusercontent.com/"+repository+"/master/data.json"
            self.log.info("Sending dataUrl to "+self.container_name+" container:"+dataUrl)
            cmd=""
            for commands in self.cmd:
                if not cmd:
                    cmd=cmd+commands
                else:
                    cmd=cmd+" "+commands
            for commands in self.get_data_setup_args():
                cmd = cmd + " " + commands
            cmd = cmd+" dcat-data-url="+dataUrl
            self.log.info("executing: "+cmd)
            response = yield self.docker("exec_create",container=self.container_name,cmd=cmd)
            response = yield self.docker("exec_start",response["Id"]);
            self.log.info(response)

            self.github_file_copies(repository)

    @gen.coroutine
    def start(self,credential, image=None, extra_create_kwargs=None,
        extra_start_kwargs=None, extra_host_config=None):
        """Start the single-user server in a docker container. You can override
        the default parameters passed to `create_container` through the
        `extra_create_kwargs` dictionary and passed to `start` through the
        `extra_start_kwargs` dictionary.  You can also override the
        'host_config' parameter passed to `create_container` through the
        `extra_host_config` dictionary.
        Per-instance `extra_create_kwargs`, `extra_start_kwargs`, and
        `extra_host_config` take precedence over their global counterparts.
        """
        new = False
        container = yield self.get_container()
        if container is None:
            new = True
            image = image or self.container_image


            # build the dictionary of keyword arguments for create_container
            create_kwargs = dict(
                image=image,
                environment=self.get_env(),
                volumes=self.volume_mount_points,
                name=self.container_name)
            extra_create_params = {
                'username': self.user.name,
                'credential': credential
            }

            print(credential)
            self.extra_create_kwargs = recursive_format(
                self.extra_create_kwargs,
                **extra_create_params
            )
            create_kwargs.update(self.extra_create_kwargs)
            if extra_create_kwargs:
                extra_create_kwargs = recursive_format(
                    extra_create_kwargs,
                    **extra_create_params
                )
                create_kwargs.update(extra_create_kwargs)

            # build the dictionary of keyword arguments for host_config
            host_config = dict(binds=self.volume_binds, links=self.links)

            if not self.use_internal_ip:
                host_config['port_bindings'] = {8888: (self.container_ip,)}

            host_config.update(self.extra_host_config)

            if extra_host_config:
                host_config.update(extra_host_config)

            self.log.debug("Starting host with config: %s", host_config)

            host_config = self.client.create_host_config(**host_config)
            create_kwargs.setdefault('host_config', {}).update(host_config)

            for volume in self.volume_binds.keys():
                yield self.docker('create_volume', name=volume, driver=self.volume_driver)

            # create the container
            resp = yield self.docker('create_container', **create_kwargs)
            self.container_id = resp['Id']
            self.log.info(
                "Created container '%s' (id: %s) from image %s",
                self.container_name, self.container_id[:7], image)

        else:
            self.log.info(
                "Found existing container '%s' (id: %s)",
                self.container_name, self.container_id[:7])

        # TODO: handle unpause
        self.log.info(
            "Starting container '%s' (id: %s)",
            self.container_name, self.container_id[:7])

        # build the dictionary of keyword arguments for start
        start_kwargs = {}
        start_kwargs.update(self.extra_start_kwargs)
        self.log.debug(start_kwargs)
        if extra_start_kwargs:
            start_kwargs.update(extra_start_kwargs)

        self.log.debug(start_kwargs)
        # start the container
        yield self.docker('start', self.container_id, **start_kwargs)
        return new

    @gen.coroutine
    def stop(self, now=False):
        """Stop the container
        Consider using pause/unpause when docker-py adds support
        """
        self.log.info(
            "Stopping container %s (id: %s)",
            self.container_name, self.container_id[:7])
        yield self.docker('stop', self.container_id)

        if self.remove_containers:
            self.log.info(
                "Removing container %s (id: %s)",
                self.container_name, self.container_id[:7])
            # remove the container, as well as any associated volumes
            yield self.docker('remove_container', self.container_id, v=True)

        self.clear_state()

    def clear_state(self):
        """clear pid state"""
        super(DockerProcessSpawner, self).clear_state()
        self.container_id = ''
