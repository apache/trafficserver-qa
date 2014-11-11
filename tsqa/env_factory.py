'''
Environment factory
    Class that will make builds of <SOURCE CODE> with optional env/configure flags
    This will maintain a set of unique "environments" (built code) and will return
    copies of these environments to callers

'''

import subprocess
import tempfile
import os
import copy
import shutil
import json

from collections import MutableMapping

# local imports
from env import Layout, Environment
from utils import merge_dicts, configure_list

SOURCE_DIR = '/home/thjackso/src/trafficserver'
TMP_DIR = '/home/thjackso/src/tsqa/tmp'


class BuildCache(MutableMapping):
    '''
    Cache environments on disk

    This is just a mapping of source_hash -> key -> installed_dir
    '''
    cache_map_filename = 'env_cache_map.json'

    def __init__(self, cache_dir):
        super(BuildCache, self).__init__()
        self.cache_dir = cache_dir

        if not os.path.isdir(self.cache_dir):
            os.makedirs(self.cache_dir)

        self._dict = {}

        self.load_cache()

    @property
    def cache_map_file(self):
        return os.path.join(self.cache_dir, self.cache_map_filename)

    def load_cache(self):
        '''
        Load the cache from disk
        '''
        try:
            with open(self.cache_map_file) as fh:
                cache = json.load(fh)
        except IOError:
            return

        changed = False  # whether we changed the cache file, and need to write it out
        # verify that all of those directories exist, clean them out if they don't
        for source_hash, env_map in cache.items():
            # if the directory doesn't exist
            for key, path in env_map.items():
                if not os.path.isdir(path):
                    del cache[source_hash][key]
                    changed = True
            # if the source_hash level key is now empty
            if len(cache[source_hash]) == 0:
                del cache[source_hash]
                changed = True

        self._dict = cache
        if changed:  # if we changed it, lets write it out to disk
            self.save_cache()

    def save_cache(self):
        '''
        Write the cache out to disk
        '''
        with open(self.cache_map_file, 'w') as fh:
            fh.write(json.dumps(self._dict))

    def __setitem__(self, key, val):
        self._dict[key] = val
        self.save_cache()

    def __delitem__(self, key):
        del self._dict[key]
        self.save_cache()

    def __getitem__(self, key):
        return self._dict[key]

    def __iter__(self):
        return iter(self._dict)

    def __len__(self):
        return len(self._dict)

    def __del__(self):
        self.save_cache()


class EnvironmentFactory(object):
    '''
    Create environments with given configure/env s
    Source_dir is a git repo, and we will return environments cached by
    git hash, configure, and env
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

        # TODO: ensure this directory exists?
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
        # TODO: re-enable, disabled just to speed it up
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



if __name__ == '__main__':
    ef = EnvironmentFactory(SOURCE_DIR, os.path.join(TMP_DIR, 'base_envs'))
    ef.get_environment()
