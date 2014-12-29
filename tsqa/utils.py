from collections import MutableMapping
import os
import json
import sys
import subprocess
import socket
import logging
import time

tsqa_logger = None
tsqa_log_level = logging.INFO
tsqa_log_levels = {
    'CRITICAL': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARN': logging.WARNING,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
    'NOTSET': logging.NOTSET
}

def set_log_level(log_level):
    '''
    Set the global log level (override with env var TSQA_LOG_LEVEL).  Must be called
    before first get_logger()
    '''

    global tsqa_log_level
    tsqa_log_level = log_level

def get_log_level():
    '''
    Get the global log level (override with env var TSQA_LOG_LEVEL).
    '''

    if os.environ.has_key('TSQA_LOG_LEVEL'):
        log_level = os.environ['TSQA_LOG_LEVEL'].upper()

        if tsqa_log_levels.has_key(log_level):
            return tsqa_log_levels[log_level]

    return tsqa_log_level

def set_logger(logger):
    '''
    Set/replace the global logger
    '''

    global tsqa_logger
    tsqa_logger = logger

def get_logger():
    '''
    Get the global logger
    '''

    global tsqa_logger

    if tsqa_logger:
        return tsqa_logger

    tsqa_logger = logging.getLogger()
    tsqa_logger.setLevel(get_log_level())
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s %(asctime)-15s - %(message)s"))
    tsqa_logger.addHandler(handler)

    return tsqa_logger

def poll_interfaces(hostports, **kwargs):
    '''  Block until we can successfully connect to all ports or timeout

    :param hostports:
    :param kwargs: optional timeout_sec
    '''

    connect_timeout_sec = 1
    poll_sleep_sec = 1

    if kwargs.has_key('timeout_sec'):
        timeout = time.time() + kwargs['timeout_sec']
    else:
        timeout = time.time() + 5

    hostports = hostports[:] # don't modify the caller's hostports

    while timeout > time.time():
        for hostport in hostports[:]: # don't modify our hostports copy during iteration
            hostname = hostport[0]
            port = hostport[1]

            if get_logger().isEnabledFor(logging.DEBUG):
                get_logger().debug("Checking interface '%s:%d'", hostname, port)

            # This supports IPv6

            try:
                s = socket.create_connection((hostname, port), timeout=connect_timeout_sec)
                s.close()
                hostports.remove(hostport)

                if get_logger().isEnabledFor(logging.DEBUG):
                    get_logger().debug("Interface '%s:%d' is up", hostname, port)
            except:
                pass

        if not hostports:
            break

        time.sleep(poll_sleep_sec)

    if hostports:
        raise Exception("Timeout waiting for interfaces: {0}".format(
                        reduce(lambda x, y: str(x) + ',' + str(y), hostports)))

    if get_logger().isEnabledFor(logging.DEBUG):
        get_logger().debug("All interfaces are up")

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
        if stderr:
            raise Exception('Error {0} running: {1}\n{2}'.format(p.returncode, args[0], stderr))
        else:
            raise Exception('Error {0} running: {1}'.format(p.returncode, args[0]))

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
