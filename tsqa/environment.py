import subprocess
import tempfile
import os
import copy
import shutil
import tsqa.utils
import sys

import tsqa.configs
import tsqa.utils
import logging


class EnvironmentFactory(object):
    '''
    Make builds of <SOURCE CODE> with optional env/configure flags
    This uses a BuildCache to maintain a set of unique "layouts" (built code on disk)
    and will return copies of these in environments to callers
    '''
    class_environment_stash = None
    def __init__(self,
                 source_dir,
                 env_cache_dir,
                 default_configure=None,
                 default_env=None):
        # if no one made the cache class, make it
        if self.class_environment_stash is None:
            self.class_environment_stash = tsqa.utils.BuildCache(env_cache_dir)

        # TODO: ensure this directory exists? (and is git?)
        self.source_dir = source_dir
        self.log = logging.getLogger(__name__)
        self.env_cache_dir = env_cache_dir  # base directory for environment caching

        if default_configure is not None:
            self.default_configure = default_configure
        else:
            self.default_configure = {}

        if default_env is not None:
            self.default_env = default_env
        else:
            self.default_env = copy.copy(os.environ)

    def autoreconf(self):
        '''
        Autoreconf to make the configure script
        '''
        kwargs = {
            'cwd': self.source_dir,
            'env': self.default_env,
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE
        }

        if self.log.isEnabledFor(logging.DEBUG):
            kwargs['stdout'] = sys.stdout.fileno()
            kwargs['stderr'] = sys.stderr.fileno()

        # run autoreconf in source tree
        try:
            tsqa.utils.run_sync_command(['make', 'distclean'], **kwargs)
        except:
            pass
        tsqa.utils.run_sync_command(['autoreconf', '-if'], **kwargs)

    @property
    def source_hash(self):
        '''
        Return the git hash of the source directory
        '''
        if not hasattr(self , '_source_hash'):
            tmp, _ = tsqa.utils.run_sync_command(['git', 'rev-parse', 'HEAD'],
                                                 cwd=self.source_dir,
                                                 stdout=subprocess.PIPE,
                                                 stderr=subprocess.PIPE,
                                                 )
            self._source_hash = tmp.strip()
        return self._source_hash

    @property
    def environment_stash(self):
        '''
        Return your source_dir's section of the cache
        '''
        if self.source_hash not in self.class_environment_stash:
            self.class_environment_stash[self.source_hash] = {}

        return self.class_environment_stash[self.source_hash]

    def _get_key(self, *args):
        '''
        Take list of dicts and make a nice tuple list to use as a key
        take that and then hash it
        '''
        key = []
        for arg in args:
            sub_key = []
            for k in sorted(arg):
                sub_key.append((k, arg[k]))
            key.append(tuple(sub_key))
        return str(hash(tuple(key)))  # return a string since JSON doesn't like ints as keys

    def get_environment(self, configure=None, env=None):
        '''
        Build (or return cached) environment with configure/env
        '''
        # set defaults, if none where passed in
        if configure is None:
            configure = self.default_configure
        else:
            configure = tsqa.utils.merge_dicts(self.default_configure, configure)
        if env is None:
            env = self.default_env
        else:
            env = tsqa.utils.merge_dicts(self.default_env, env)

        # TODO: global?
        # TODO: other things that can change the build...
        env_key = {}
        for whitelisted_key in ('PATH',):
            env_key[whitelisted_key] = env.get(whitelisted_key)

        key = self._get_key(configure, env_key)
        self.log.debug('Key is: %s, args are: %s %s' % (key, configure, env_key))

        # if we don't have it built already, lets build it
        if key not in self.environment_stash:
            self.autoreconf()
            builddir = tempfile.mkdtemp()

            kwargs = {
                'cwd': builddir,
                'env': env,
                'stdout': subprocess.PIPE,
                'stderr': subprocess.PIPE
            }

            if self.log.isEnabledFor(logging.DEBUG):
                kwargs['stdout'] = sys.stdout.fileno()
                kwargs['stderr'] = sys.stderr.fileno()

            # configure
            args = [os.path.join(self.source_dir, 'configure'), '--prefix=/'] + tsqa.utils.configure_list(configure)
            tsqa.utils.run_sync_command(args, **kwargs)

            # make
            tsqa.utils.run_sync_command(['make', '-j'], **kwargs)
            installdir = tempfile.mkdtemp(dir=self.env_cache_dir)

            # make install
            tsqa.utils.run_sync_command(['make', 'install', 'DESTDIR={0}'.format(installdir)], **kwargs)

            shutil.rmtree(builddir)  # delete builddir, not useful after install
            # stash the env
            self.environment_stash[key] = installdir

        # create a layout
        layout = Layout(self.environment_stash[key])

        # return an environment cloned from that layout
        ret = Environment()
        ret.clone(layout=layout)
        return ret


class Layout:
    """
    The Layout class is responsible for the set of installation paths within a
    prefixed Traffic Server instance.

    # For now, just use a static set of directories relative to TS_ROOT. I
    # don't think that this will actually work in the general case, since there
    # are still a few paths that are defined by the build that you just have to
    # know. Maybe we can deal with that by overriding config in the environment
    # when we execute tools.
    """
    suffixes = {
        'bindir': 'bin',
        'includedir': 'include',
        'libdir': 'lib',
        'logdir': 'var/log',
        'plugindir': 'libexec/trafficserver',
        'runtimedir': 'var/trafficserver',
        # TODO: change back to var/run after fixing traffic_manager, who doesn't honor proxy.config.local_state_dir
        #'runtimedir': 'var/run',
        'sysconfdir': 'etc/trafficserver',
    }

    def __init__(self, prefix):
        self.prefix = prefix
        self.log = logging.getLogger(__name__)

    def __getattr__(self, name):
        # Raise an error for suffixes we don't know about
        if name not in Layout.suffixes:
            raise AttributeError(name)
        # If our prefix is not set, we don't have any other paths.
        if self.prefix is None:
            return None
        # Yay, we have a path.
        return str(os.path.join(self.prefix, Layout.suffixes[name]))

    @classmethod
    def ParseFromLayout(self, path):
        """
        Parse the output of traffic_layout to instantiate a Layout object. This
        has a terrible name, and probably needs to die, but it is helpful for
        now since we can use it to bootstrap an environment from something we
        already have installed.
        """
        layout = Layout(None)
        proc = subprocess.Popen(path, shell=False, stderr=open('/dev/null'), stdout=subprocess.PIPE)
        stdout, _ = proc.communicate()
        for line in stdout.splitlines():
            key, val = line.split(': ', 1)
            setattr(layout, key.lower(), val)

        return layout


class Environment:
    @property
    def shell_env(self):
        environ = copy.copy(os.environ)
        environ['TS_ROOT'] = self.layout.prefix

        if environ.has_key('LD_LIBRARY_PATH') and self.layout.libdir not in environ['LD_LIBRARY_PATH'].split(':'):
            environ['LD_LIBRARY_PATH'] = self.layout.libdir + ':' + environ['LD_LIBRARY_PATH']
        else:
            environ['LD_LIBRARY_PATH'] = self.layout.libdir
        return environ

    def __exec_cop(self):
        path = os.path.join(self.layout.bindir, 'traffic_cop')
        cmd = [path, '--debug', '--stdout']

        with open(os.path.join(self.layout.logdir, 'cop.log'), 'w+') as logfile:
            self.cop = subprocess.Popen(cmd,
                                        env=self.shell_env,
                                        stdout=logfile,
                                        stderr=logfile,
                                        )
            # TODO: more specific exception?
            try:
                tsqa.utils.poll_interfaces(self.hostports)
            except:
                self.stop()  # make sure to stop the daemons
                raise

            self.cop.poll()
            if self.cop.returncode is not None:
                raise Exception(self.cop.returncode, self.layout.prefix)

    def __init__(self, layout=None):
        """
        Initialize a new Environment.
        """
        self.log = logging.getLogger(__name__)
        self.cop = None
        # TODO: parse config? Don't like the separate hostports...
        self.hostports = []
        if layout:
            self.layout = layout
        else:
            self.layout = None

    def create(self):
        """
        """
        if self.layout is None:
            self.layout = Layout(tempfile.mkdtemp())
        else:
            os.makedirs(self.layout.prefix)

        # Make any other directories we need.
        os.makedirs(os.path.join(self.layout.sysconfdir, "body_factory"))

    def clone(self, layout=None):
        """
        Clone the given layout to this environment's prefix
        """
        # First, make the prefix directory.
        if self.layout is None:
            self.layout = Layout(tempfile.mkdtemp(prefix=os.environ.get('TSQA_LAYOUT_PREFIX', '')))
        else:
            os.makedirs(self.layout.prefix)
        os.chmod(self.layout.prefix, 0777)  # Make the tmp dir readable by all

        # copy all files from old layout to new one
        for item in os.listdir(layout.prefix):
            src_path = os.path.join(layout.prefix, item)
            dst_path = os.path.join(self.layout.prefix, item)
            # if its the bindir, lets symlink in everything
            if item == layout.suffixes['bindir']:
                os.makedirs(dst_path)  # make the dest dir
                for bin_item in os.listdir(src_path):
                     os.symlink(os.path.join(src_path, bin_item),
                                os.path.join(dst_path, bin_item),
                                )

            elif os.path.isdir(src_path):
                shutil.copytree(src_path,
                                dst_path,
                                symlinks=True,
                                ignore=None,
                                )

            elif os.path.isfile(src_path):
                shutil.copyfile(src_path, dst_path)

        # make sure that all suffixes in new layout exist
        for name in self.layout.suffixes:
            dirname = getattr(self.layout, name)
            if not os.path.exists(dirname):
                os.makedirs(dirname, 0777)
            else:
                os.chmod(dirname, 0777)

        http_server_port = tsqa.utils.bind_unused_port()[1]
        manager_mgmt_port = tsqa.utils.bind_unused_port()[1]
        admin_port = tsqa.utils.bind_unused_port()[1]

        self.hostports = [('127.0.0.1', http_server_port),
                          ('127.0.0.1', manager_mgmt_port),
                          ('127.0.0.1', admin_port),
                          ]

        # overwrite a few things that need to be changed to have a unique env
        records = tsqa.configs.RecordsConfig(os.path.join(self.layout.sysconfdir, 'records.config'))
        records['CONFIG'].update({
            'proxy.config.config_dir': self.layout.sysconfdir,
            'proxy.config.body_factory.template_sets_dir': os.path.join(self.layout.sysconfdir, 'body_factory'),
            'proxy.config.plugin.plugin_dir': self.layout.plugindir,
            'proxy.config.bin_path': self.layout.bindir,
            'proxy.config.log.logfile_dir': self.layout.logdir,
            'proxy.config.local_state_dir': self.layout.runtimedir,
            'proxy.config.http.server_ports': str(http_server_port),  # your own listen port
            'proxy.config.process_manager.mgmt_port': manager_mgmt_port,  # your own listen port
            'proxy.config.admin.autoconf_port': admin_port,
            'proxy.config.diags.show_location': 1,
            'proxy.config.admin.user_id': '#-1',

            # set the process_server timeouts to 0 (faster startup)
            'proxy.config.lm.pserver_timeout_secs': 0,
            'proxy.config.lm.pserver_timeout_msecs': 0,
        })
        records.write()

        os.chmod(os.path.join(os.path.dirname(self.layout.runtimedir)), 0777)
        os.chmod(os.path.join(self.layout.runtimedir), 0777)

        # write out a conveinence script to
        with open(os.path.join(self.layout.prefix, 'run'), 'w') as runscript:
            runscript.write('#! /usr/bin/env sh\n\n')
            runscript.write('# run PROGRAM [ARGS ...]\n')
            runscript.write('# Run a Traffic Server program in this environment\n\n')
            for k, v in self.shell_env.iteritems():
                runscript.write('{0}="{1}"\n'.format(k, v))
                runscript.write('export {0}\n\n'.format(k))
            runscript.write('exec "$@"\n')

    def destroy(self):
        """
        Tear down the environment. Kill any running processes and remove any
        installed files.
        """
        self.stop()
        shutil.rmtree(self.layout.prefix, ignore_errors=True)
        self.layout = Layout(None)

    def start(self):
        if self.running():  # if its already running, don't start another one
            raise Exception('traffic cop already started')
        self.log.debug("Starting traffic cop")
        assert(os.path.isfile(os.path.join(self.layout.sysconfdir, 'records.config')))
        self.__exec_cop()
        self.log.debug("Started traffic cop: %s", self.cop)

    # TODO: exception if already stopped?
    # TODO: more graceful stop?
    def stop(self):
        self.log.debug("Killing traffic cop: %s", self.cop)
        if self.cop is not None:
            self.cop.kill()
            self.cop.terminate()  # TODO: remove?? or wait...

    def running(self):
        if self.cop is None:
            return False
        self.cop.poll()
        return self.cop.returncode is None  # its running if it hasn't died


if __name__ == '__main__':
    SOURCE_DIR = os.getenv('TSQA_SRC_DIR', '~/trafficserver')
    TMP_DIR = os.getenv('TSQA_TMP_DIR','/tmp/tsqa')
    ef = EnvironmentFactory(SOURCE_DIR, os.path.join(TMP_DIR, 'base_envs'))
    ef.get_environment()
