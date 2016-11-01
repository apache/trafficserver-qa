#  Licensed to the Apache Software Foundation (ASF) under one
#  or more contributor license agreements.  See the NOTICE file
#  distributed with this work for additional information
#  regarding copyright ownership.  The ASF licenses this file
#  to you under the Apache License, Version 2.0 (the
#  "License"); you may not use this file except in compliance
#  with the License.  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import subprocess
import tempfile
import os
import copy
import shutil
import tsqa.utils
import sys
import time
import multiprocessing
import hashlib
import json

import tsqa.configs
import tsqa.utils
import logging

log = logging.getLogger(__name__)


class EnvironmentFactory(object):
    '''
    Make builds of <SOURCE CODE> with optional env/configure flags
    This uses a BuildCache to maintain a set of unique "layouts" (built code on disk)
    and will return copies of these in environments to callers
    '''
    class_environment_stash = None

    # key -> exception
    negative_cache = {}

    def __init__(self,
                 source_dir,
                 env_cache_dir,
                 default_configure=None,
                 default_env=None,
                 build_dir=None):
        # if no one made the cache class, make it
        if self.class_environment_stash is None:
            self.class_environment_stash = tsqa.utils.BuildCache(env_cache_dir)

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

        self.build_dir = build_dir

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

        if log.isEnabledFor(logging.DEBUG):
            # if this is debug, lets not capture the output and let it go to
            # stdout and stderr
            kwargs['stdout'] = None
            kwargs['stderr'] = None

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
        hval = hashlib.md5()
        for arg in args:
            for k in sorted(arg):
                hval.update(k)
                hval.update(str(arg[k]))
        return hval.hexdigest()

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
        log.debug('Key is: %s, args are: %s %s' % (key, configure, env_key))

        # if we don't have it built already, lets build it
        if key not in self.environment_stash:
            if key in EnvironmentFactory.negative_cache:
                raise EnvironmentFactory.negative_cache[key]
            try:
                self.autoreconf()
                # if we have a build dir configured, lets use thatm otherwise
                # lets use a tmp one
                builddir = self.build_dir or tempfile.mkdtemp()

                kwargs = {
                    'cwd': builddir,
                    'env': env,
                    'stdout': subprocess.PIPE,
                    'stderr': subprocess.PIPE
                }

                if log.isEnabledFor(logging.DEBUG):
                    # if this is debug, lets not capture the output and let it go to
                    # stdout and stderr
                    kwargs['stdout'] = None
                    kwargs['stderr'] = None
                log.info('Starting build ({0}): configure {1}'.format(key, configure))

                # configure
                args = [os.path.join(self.source_dir, 'configure'), '--prefix=/'] + tsqa.utils.configure_list(configure)
                tsqa.utils.run_sync_command(args, **kwargs)

                # make
                tsqa.utils.run_sync_command(['make', '-j{0}'.format(multiprocessing.cpu_count())], **kwargs)
                installdir = tempfile.mkdtemp(dir=self.env_cache_dir)

                # make install
                tsqa.utils.run_sync_command(['make', 'install', 'DESTDIR={0}'.format(installdir)], **kwargs)

                # if we had to create a tmp dir, we should delete it
                if self.build_dir is None:
                    shutil.rmtree(builddir)
                # stash the env
                self.environment_stash[key] = {
                        'path': installdir,
                        'configuration': args,
                        'env': env_key,
                }
                log.info('Build completed ({0}): configure {1}'.format(key, configure))
            except Exception as e:
                EnvironmentFactory.negative_cache[key] = e
                raise

        # create a layout
        layout = Layout(self.environment_stash[key]['path'])

        # return an environment cloned from that layout
        ret = Environment()
        ret.clone(layout=layout)
        return ret


class Layout(object):
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
        if prefix is not None:
            prefix = os.path.abspath(prefix)
        self.prefix = prefix

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
        stdout, _ = tsqa.utils.run_sync_command(path,
                                                shell=False,
                                                stdout=subprocess.PIPE,
                                                )
        for line in stdout.splitlines():
            key, val = line.split(': ', 1)
            setattr(layout, key.lower(), val)

        return layout


class Environment(object):
    '''
    This is the core of tsqa. An environment is a directory (effectively a root dir)
    with code and configs installed into it. This object is also responsible for
    the daemon that will run out of this environment. All environments should be
    sandboxed (separate directories), and failures in one environment should not
    cause failures in other environments.

    '''
    def features(self):
        out = subprocess.check_output([
            os.path.join(self.layout.bindir, 'traffic_layout'),
            '-fj',
        ])
        return json.loads(out.decode("utf-8"))

    @property
    def shell_env(self):
        environ = copy.copy(os.environ)
        environ['TS_ROOT'] = self.layout.prefix

        for env_key in ('LD_LIBRARY_PATH',  # for *nix
                        'DYLD_LIBRARY_PATH',  # for mac
                        ):
            if environ.has_key(env_key):
                if self.layout.libdir not in environ[env_key].split(':'):
                    environ[env_key] = self.layout.libdir + ':' + environ[env_key]
            else:
                environ[env_key] = self.layout.libdir

        return environ

    def __exec_cop(self):
        path = os.path.join(self.layout.bindir, 'traffic_cop')
        cmd = [path, '--debug', '--stdout']

        with open(os.path.join(self.layout.logdir, 'cop.log'), 'w+') as logfile:
            self.cop = subprocess.Popen(
                cmd,
                env=self.shell_env,
                stdout=logfile,
                stderr=logfile,
            )
            start = time.time()
            # TODO: more specific exception?
            try:
                tsqa.utils.poll_interfaces(self.hostports)
            except:
                self.stop()  # make sure to stop the daemons
                raise
            log.debug('traffic_cop took {0}s to start up'.format(time.time() - start))

            self.cop.poll()
            if self.cop.returncode is not None:
                raise Exception(self.cop.returncode, self.layout.prefix)

    def __init__(self, layout=None):
        """
        Initialize a new Environment.
        """
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
            self.layout = Layout(tempfile.mkdtemp(
                prefix=os.environ.get('TSQA_LAYOUT_PREFIX', 'tsqa.env.'),
                dir=os.environ.get('TSQA_LAYOUT_DIR', None)),
            )
        else:
            os.makedirs(self.layout.prefix)
        os.chmod(self.layout.prefix, 0777)  # Make the tmp dir readable by all

        # TODO: handle sock files (copytree doesn't like them!)
        # copy all files from old layout to new one
        for item in os.listdir(layout.prefix):
            src_path = os.path.join(layout.prefix, item)
            dst_path = os.path.join(self.layout.prefix, item)
            # if its the bindir, lets symlink in everything
            if item == layout.suffixes['bindir']:
                os.makedirs(dst_path)  # make the dest dir
                for bin_item in os.listdir(src_path):
                     os.symlink(
                        os.path.join(src_path, bin_item),
                        os.path.join(dst_path, bin_item),
                     )

            elif os.path.islink(src_path):
                linkto = os.readlink(src_path)
                os.symlink(linkto, dst_path)

            elif os.path.isdir(src_path):
                shutil.copytree(
                    src_path,
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

        self.hostports = [
            ('127.0.0.1', http_server_port),
            ('127.0.0.1', manager_mgmt_port),
            ('127.0.0.1', admin_port),
        ]

        # TODO: clear out all configs!
        # truncate remap.config
        open(os.path.join(self.layout.sysconfdir, 'remap.config'), 'w').truncate()
        open(os.path.join(self.layout.sysconfdir, 'records.config'), 'w').truncate()

        # overwrite a few things that need to be changed to have a unique env
        records = tsqa.configs.RecordsConfig(os.path.join(self.layout.sysconfdir, 'records.config'))
        records['CONFIG'] = {
            'proxy.config.config_dir': self.layout.sysconfdir,
            'proxy.config.body_factory.template_sets_dir': os.path.join(self.layout.sysconfdir, 'body_factory'),
            'proxy.config.plugin.plugin_dir': self.layout.plugindir,
            'proxy.config.bin_path': self.layout.bindir,
            'proxy.config.log.logfile_dir': self.layout.logdir,
            'proxy.config.local_state_dir': self.layout.runtimedir,
            'proxy.config.http.server_ports': str(http_server_port),  # your own listen port
            'proxy.config.process_manager.mgmt_port': manager_mgmt_port,  # your own listen port
            'proxy.config.admin.synthetic_port': admin_port,
            'proxy.config.admin.autoconf_port': admin_port,  # support pre ATS 6.x
            'proxy.config.admin.user_id': '#-1',

            # a bunch of debug options
            'proxy.config.diags.show_location': 1,
            'proxy.config.diags.output.diag': 'OL',
            'proxy.config.diags.output.debug': 'OL',
            'proxy.config.diags.output.status': 'OL',
            'proxy.config.diags.output.note': 'OL',
            'proxy.config.diags.output.warning': 'OL',
            'proxy.config.diags.output.error': 'OL',
            'proxy.config.diags.output.fatal': 'OL',
            'proxy.config.diags.output.alert': 'OL',
            'proxy.config.diags.output.emergency': 'OL',

            # set the process_server timeouts to 0 (faster startup)
            'proxy.config.lm.pserver_timeout_secs': 0,
            'proxy.config.lm.pserver_timeout_msecs': 0,
        }
        records.write()

        os.chmod(os.path.join(os.path.dirname(self.layout.runtimedir)), 0777)
        os.chmod(os.path.join(self.layout.runtimedir), 0777)

        # write out a convenience script to
        with open(os.path.join(self.layout.prefix, 'run'), 'w') as runscript:
            runscript.write('#! /usr/bin/env sh\n\n')
            runscript.write('# run PROGRAM [ARGS ...]\n')
            runscript.write('# Run a Traffic Server program in this environment\n\n')
            for k, v in self.shell_env.iteritems():
                runscript.write('{0}="{1}"\n'.format(k, v))
                runscript.write('export {0}\n\n'.format(k))
            runscript.write('exec "$@"\n')

        os.chmod(os.path.join(self.layout.prefix, 'run'), 0755)


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
        log.debug("Starting traffic cop")
        assert(os.path.isfile(os.path.join(self.layout.sysconfdir, 'records.config')))
        self.__exec_cop()
        log.debug("Started traffic cop: %s", self.cop)

    # TODO: exception if already stopped?
    def stop(self):
        log.debug("Stopping traffic cop: %s", self.cop)
        if self.running():
            self.cop.kill()
            # wait for a max of 2s
            stoptime = time.time() + 2
            while time.time() < stoptime:
                # if we got a returncode, we exited
                if self.cop.poll() is not None:
                    return
                time.sleep(0.1)
            log.error('Unable to stop traffic_cop: {0}'.format(self.cop))
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
