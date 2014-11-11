import os
import shutil
import tempfile
import subprocess

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

