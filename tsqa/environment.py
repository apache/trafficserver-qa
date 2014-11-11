import subprocess
import tempfile
import os
import copy
import shutil
import json
from utils import merge_dicts, configure_list


class EnvironmentFactory(object):
    '''
    Create environments with given configure/env s
    Source_dir is a git repo, and we will return environments cached by
    git hash, configure, and env

    Class that will make builds of <SOURCE CODE> with optional env/configure flags
    This will maintain a set of unique "environments" (built code) and will return
    copies of these environments to callers
    '''
    class_environment_stash = None
    def __init__(self,
                 source_dir,
                 env_cache_dir,
                 default_configure=None,
                 default_env=None):
        # if no one made the cache class, make it
        if self.class_environment_stash is None:
            self.class_environment_stash = BuildCache(env_cache_dir)

        # TODO: ensure this directory exists? (and is git?)
        self.source_dir = source_dir

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
        # run autoreconf in source tree
        p = subprocess.Popen(['autoreconf'],
                             cwd=self.source_dir,
                             env=self.default_env,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             )
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            raise Exception('Unable to autoreconf {0}'.format(self.source_dir))

    @property
    def source_hash(self):
        '''
        Return the git hash of the source directory
        '''
        if not hasattr(self , '_source_hash'):
            tmp, _ = self._run_sync_command(['git', 'rev-parse', 'HEAD'],
                                            cwd=self.source_dir,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE,
                                            )
            self._source_hash = tmp.strip()
        return self._source_hash

    def _run_sync_command(self, *args, **kwargs):
        '''
        Helper to run a command synchronously
        '''
        p = subprocess.Popen(*args, **kwargs)
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            raise Exception('Error running: {0}\n{1}'.format(args[0], stderr))
        return stdout, stderr

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
            configure = merge_dicts(self.default_configure, configure)
        if env is None:
            env = self.default_env
        else:
            env = merge_dicts(self.default_env, env)

        key = self._get_key(configure, env)

        # if we don't have it built already, lets build it
        if key not in self.environment_stash:
            self.autoreconf()
            builddir = tempfile.mkdtemp()

            # configure
            args = [os.path.join(self.source_dir, 'configure'), '--prefix=/'] + configure_list(configure)
            self._run_sync_command(args,
                                   cwd=builddir,
                                   env=env,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   )

            # make
            self._run_sync_command(['make', '-j'],
                                   cwd=builddir,
                                   env=env,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   )
            installdir = tempfile.mkdtemp(dir=self.env_cache_dir)

            # make install
            self._run_sync_command(['make', 'install', 'DESTDIR={0}'.format(installdir)],
                                   cwd=builddir,
                                   env=env,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   )

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
    # For now, just use a static set of directories relative to TS_ROOT. I
    # don't think that this will actually work in the general case, since there
    # are still a few paths that are defined by the build that you just have to
    # know. Maybe we can deal with that by overriding config in the environment
    # when we execute tools.
    suffixes = {
        'bindir': 'bin',
        'includedir': 'include',
        'libdir': 'lib',
        'logdir': 'var/log',
        'plugindir': 'lib/plugins',
        'runtimedir': 'var/run',
        'sysconfdir': 'etc/trafficserver',
    }

    configs = (
        'cache.config',
        'cluster.config',
        'congestion.config',
        'hosting.config',
        'icp.config',
        'ip_allow.config',
        'log_hosts.config',
        'logs_xml.config',
        'parent.config',
        'plugin.config',
        'prefetch.config',
        'records.config',
        'remap.config',
        'socks.config',
        'splitdns.config',
        'ssl_multicert.config',
        'stats.config.xml',
        'storage.config',
        'trafficserver-release',
        'update.config',
        'vaddrs.config',
        'volume.config',
    )

    """
    The Layout class is responsible for the set of installation paths within a
    prefixed Traffic Server instance.
    """
    def __init__(self, prefix):
        self.prefix = prefix

    def __getattr__(self, name):
        # Raise an error for suffixes we don't know about
        if name not in Layout.suffixes:
            raise AttributeError(name)
        # If our prefix is not set, we don't have any other paths.
        if self.prefix is None:
            return None
        # Yay, we have a path.
        return os.path.join(self.prefix, Layout.suffixes[name])

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
    def __exec_cop(self):
        path = os.path.join(self.layout.bindir, 'traffic_cop')
        logfile = os.path.join(self.layout.logdir, 'cop.log')
        cmd = [path, '--debug', '--stdout']
        environ = {'TS_ROOT': self.layout.prefix}

        # XXX We ought to be pointing traffic_cop to its records.config using
        # proxy.config.config_dir in the environment, but traffic_cop doesn't
        # look at that (yet).
        with open(os.path.join(self.layout.logdir, 'cop.log'), 'w+') as logfile:
            self.cop = subprocess.Popen(cmd,
                                        env=environ,
                                        stdin=open('/dev/null'),
                                        stdout=logfile,
                                        stderr=logfile)

    def __init__(self, layout=None):
        """
        Initialize a new Environment.
        """
        self.cop = None
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

        for d in ('logdir', 'runtimedir', 'sysconfdir'):
            os.makedirs(getattr(self.layout, d))

        # Make any other directories we need.
        os.makedirs(os.path.join(self.layout.sysconfdir, "body_factory"))

    def clone(self, layout=None):
        """
        Clone the given layout to this environment's prefix
        """
        # First, make the prefix directory.
        if self.layout is None:
            self.layout = Layout(tempfile.mkdtemp())
        else:
            os.makedirs(self.layout.prefix)

        # Take constant data directories from the parent environment.
        for d in ('bindir', 'includedir', 'libdir', 'plugindir'):
            setattr(self.layout, d, getattr(layout, d))

        os.makedirs(self.layout.logdir)
        os.makedirs(self.layout.runtimedir)
        shutil.copytree(layout.sysconfdir, self.layout.sysconfdir, symlinks=True, ignore=None)

        self.overrides = {
            'proxy.config.config_dir': self.layout.sysconfdir,
            'proxy.config.body_factory.template_sets_dir': os.path.join(self.layout.sysconfdir, 'body_factory'),
            'proxy.config.plugin.plugin_dir': self.layout.plugindir,
            'proxy.config.bin_path': self.layout.bindir,
            'proxy.config.log.logfile_dir': self.layout.logdir,
            'proxy.config.local_state_dir': self.layout.runtimedir,
        }

        # Append records.config overrides.
        with open(os.path.join(self.layout.sysconfdir, 'records.config'), 'a+') as records:
            for k, v in self.overrides.iteritems():
                records.write('CONFIG {0} STRING {1}\n'.format(k, v))

    def destroy(self):
        """
        Tear down the environment. Kill any running processes and remove any
        installed files.
        """
        self.stop()
        shutil.rmtree(self.layout.prefix, ignore_errors=True)
        self.layout = Layout(None)

    def start(self):
        assert(os.path.isfile(os.path.join(self.layout.sysconfdir, 'records.config')))
        self.__exec_cop()

    def stop(self):
        pass

    def __del__(self):
        self.destroy()


if __name__ == '__main__':
    SOURCE_DIR = '/home/thjackso/src/trafficserver'
    TMP_DIR = '/home/thjackso/src/tsqa/tmp'
    ef = EnvironmentFactory(SOURCE_DIR, os.path.join(TMP_DIR, 'base_envs'))
    ef.get_environment()
