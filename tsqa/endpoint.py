# TODO: some request/response class to load the various libary's implementations and allow for comparison

import os
import threading
import requests
import flask


from collections import defaultdict
from wsgiref.simple_server import make_server

# dict of testid -> {client_request, client_response}
REQUESTS = defaultdict(dict)


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


class DynamicHTTPEndpoint(threading.Thread):
    TRACKING_HEADER = '__cool_test_header__'

    @property
    def address(self):
        return (self.server.server_address, self.server.server_port)

    def __init__(self, port=0):
        threading.Thread.__init__(self)
        # dict to store request data in
        self.tracked_requests = {}

        self.daemon = True

        self.port = port

        self.ready = threading.Event()

        # dict of pathname (no starting /) -> function
        self.handlers = {}

        self.app = flask.Flask(__name__)
        self.app.debug = True


        @self.app.before_request
        def save_request():
            '''
            If the tracking header is set, save the request
            '''
            if flask.request.headers.get(self.TRACKING_HEADER):
                self.tracked_requests[flask.request.headers[self.TRACKING_HEADER]] = {'request': request.copy()}


        @self.app.after_request
        def save_response(response):
            '''
            If the tracking header is set, save the response
            '''
            if flask.request.headers.get(self.TRACKING_HEADER):
                self.tracked_requests[flask.request.headers[self.TRACKING_HEADER]]['response'] = response

            return response

        @self.app.route('/', defaults={'path': ''})
        @self.app.route('/<path:path>')
        def catch_all(path=''):
            # get path key
            if path in self.handlers:
                return self.handlers[path](flask.request)

            # return a 404 since we didn't find it
            return ('', 404)

        # A little magic to make flask accept *all* methods on the catch_all path
        for rule in self.app.url_map.iter_rules():
            rule.methods = None
            rule.refresh()

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
        self.server = make_server('',
                                  self.port,
                                  self.app.wsgi_app)
        # mark it as ready
        self.ready.set()
        # serve it
        self.server.serve_forever()
