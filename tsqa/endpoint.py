# TODO: some request/response class to load the various libary's implementations and allow for comparison

import os

import gevent
import gevent.greenlet
import gevent.wsgi
import grequests
from bottle import Bottle, request, hook, response  # TODO: switch to flask?? Better docs?
import threading
from collections import defaultdict
import requests

# dict of testid -> {client_request, client_response}
REQUESTS = defaultdict(dict)


# TODO: something which can do the endpoint registration with a decorator
class endpoint(object):
    def __get__(self, obj, objtype):
        """Support instance methods."""
        import functools
        return functools.partial(self.__call__, obj)

    def __init__(self, f):
        self.func = f
        import functools
        raise Exception(dir(functools.partial(self.__call__, f)))

    def __call__(self, *args):
        raise Exception(args)
        self.func(*args)


class TrackingRequests():
    def __init__(self, endpoint):
        self.endpoint = endpoint

    def __getattr__(self, name):
        def handlerFunction(*args,**kwargs):
            func = getattr(requests, name)

            # set some kwargs
            # set the tracking header
            if 'headers' not in kwargs:
                kwargs['headers'] = {}
            key = self.endpoint.get_tracking_key()
            kwargs['headers'][self.endpoint.TRACKING_HEADER] = key

            ret = {}
            resp = func(*args, **kwargs)

            server_resp = self.endpoint.get_tracking_by_key(key)

            # TODO: create intermediate objects that you can compare
            ret['client_request'] = resp.request
            ret['client_response'] = resp
            ret['server_request'] = server_resp['request']
            ret['server_response'] = server_resp['response']

            return ret

        return handlerFunction

# TODO: better webserver? Flask is okay, but gevent is... not great
# TODO: force http access log somewhere else
class DynamicHTTPEndpoint(threading.Thread):
    TRACKING_HEADER = '__cool_test_header__'

    @property
    def address(self):
        return self.server.address

    def __init__(self):
        threading.Thread.__init__(self)
        # dict to store request data in
        self.tracked_requests = {}

        self.daemon = True

        self.ready = threading.Event()

        # dict of pathname (no starting /) -> function
        self.handlers = {}

        self.app = Bottle()


        @self.app.hook('before_request')
        def save_request():
            '''
            If the tracking header is set, save the request
            '''
            if request.headers.get(self.TRACKING_HEADER):
                self.tracked_requests[request.headers[self.TRACKING_HEADER]] = {'request': request.copy()}


        @self.app.hook('after_request')
        def save_response():
            '''
            If the tracking header is set, save the response
            '''
            if request.headers.get(self.TRACKING_HEADER):
                self.tracked_requests[request.headers[self.TRACKING_HEADER]]['response'] = response

        @self.app.route('/', defaults={'path': ''})
        @self.app.route('/<path:path>')
        def catch_all(path=''):
            # get path key
            if path in self.handlers:
                return self.handlers[path](request)

            # return a 404 since we didn't find it
            return 'defualtreturn: ' + path + '\n'

    def get_tracking_key(self):
        '''
        Return a new key for tracking a request by key
        '''
        key = str(len(self.tracked_requests))
        self.tracked_requests[key] = {}
        return key

    def get_tracking_by_key(self, key):
        '''
        Return tracking data by key
        '''
        if key not in self.tracked_requests:
            raise Exception()
        return self.tracked_requests[key]

    def normalize_path(self, path):
        '''
        Normalize the path, since its common (and convenient) to start with / in your paths
        '''
        if path.startswith('/'):
            return path[1:]
        return path

    def add_handler(self, path, func):
        '''
        Add a new handler attached to a specific path
        '''
        path = self.normalize_path(path)
        if path in self.handlers:
            raise Exception()
        self.handlers[path] = func

    def remove_handler(self, path):
        '''
        remove a handler attached to a specific path
        '''
        path = self.normalize_path(path)
        if path not in self.handlers:
            raise Exception()
        del self.handlers[path]

    def run(self):
        self.server = gevent.wsgi.WSGIServer(('', 0),
                                              self.app.wsgi,
                                              log=open(os.devnull, 'w'))
        self.server.start()
        # mark it as ready
        self.ready.set()
        # serve it
        try:
            self.server._stop_event.wait()
        finally:
            gevent.greenlet.Greenlet.spawn(self.server.stop).join()
