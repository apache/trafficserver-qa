from collections import MutableMapping
import os
import json
import sys
import subprocess
import socket

# TODO: test
def import_unittest():
    '''
    Import unittest
    '''
    if sys.version_info < (2, 7):
        return __import__('unittest2')
    else:
        return __import__('unittest')


def bind_unused_port(interface=''):
    '''
    Binds a server socket to an available port on 0.0.0.0.

    Returns a tuple (socket, port).
    '''
    sock = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((interface, 0))  # bind to all interfaces on an ephemeral port
    port = sock.getsockname()[1]
    return sock, port


# TODO: test
def run_sync_command(*args, **kwargs):
    '''
    Helper to run a command synchronously
    '''
    p = subprocess.Popen(*args, **kwargs)
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        raise Exception('Error running: {0}\n{1}'.format(args[0], stderr))
    return stdout, stderr


def merge_dicts(*args):
    '''
    Merge dicts in order

    We do them in reverse to avoid having to set/unset a lot of things
    '''
    ret = {}
    for arg in reversed(args):
        for k, v in arg.iteritems():
            if k not in ret:
                ret[k] = v
    return ret


def configure_list(configure):
    ret = []
    for k, v in configure.iteritems():
        if v is None:  # if value is None, then its just an arg
            ret.append('--{0}'.format(k))
        else:  # otherwise there was a value
            ret.append('--{0}={1}'.format(k, v))
    return ret


def configure_string_to_dict(configure_string):
    '''
    Take a configure string and break it into a dict
    '''
    ret = {}
    for part in configure_string.split():
        part = part.strip('-').strip()
        if '=' in part:
            k, v = part.split('=', 1)
        else:
            k = part
            v = None
        ret[k] = v
    return ret


class BuildCache(MutableMapping):
    '''
    Cache layouts on disk

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
