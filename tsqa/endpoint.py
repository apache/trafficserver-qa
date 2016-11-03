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

import os
import threading
import requests
import flask
import socket
import SocketServer
import ssl

from collections import defaultdict
from wsgiref.simple_server import make_server

# dict of testid -> {client_request, client_response}
REQUESTS = defaultdict(dict)


# TODO: some request/response class to load the various libary's implementations and allow for comparison
class TrackingRequests():
    '''
    This class gives you a "requests" like object that will return a dict of:
        - client_request
        - client_response
        - server_request
        - server_response
    assuming the request is going to the instance of DynamicHTTPEndpoint this object
    was created with

    In general this is useful for a proxy testing framework beause you commonly
    need to check that the proxy (for example) added a header to the request
    before the origin got it.
    '''
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
    '''
    A threaded webserver which allows you to dynamically add/remove handlers.
    This is implemented using flask (http://flask.pocoo.org/) primarily because
    it is very common and (almost more importantly) *very* picky about http
    semantics.

    To use this in a TestCase you simply need to create the thread:

        # create the thread object
        http_endpoint = tsqa.endpoint.DynamicHTTPEndpoint(port=cls.endpoint_port)
        # start the thread
        http_endpoint.start()
        # wait for the webserver to listen
        http_endpoint.ready.wait()

    At this point the webserver is listening and returning 404 for all requests.
    To register an endpoint you must (1) define a request-handler function and
    (2) add that handler to the http_endpoint.

    (1): To define a request handler you must create a function which takes a single
    argument which is the Request wrapper (http://werkzeug.pocoo.org/docs/0.10/wrappers/#werkzeug.wrappers.Request).
    Flask support a variety or return types (http://flask.pocoo.org/docs/0.10/quickstart/#about-responses),
    for this example we will simply return "hello world"

        def handler_func(request):
            return "hello world"

    (2): Now that we have a function, we can add it as a handler to a context path
        http_endpoint.add_handler('/hello', handler_func)

    '''
    TRACKING_HEADER = '__cool_test_header__'  # TODO: better name?

    @property
    def address(self):
        '''
        Return a tuple of (ip, port) that this thread is listening on.
        '''
        return (self.server.server_address, self.server.server_port)

    def __init__(self, port=0):
        threading.Thread.__init__(self)
        # dict to store request data in
        self._tracked_requests = {}
        # error in startup
        self.error = None

        self.daemon = True
        self.port = port
        self.ready = threading.Event()

        # dict of pathname (no starting /) -> function
        self._handlers = {}

        self.app = flask.Flask(__name__)
        self.app.debug = True


        @self.app.before_request
        def save_request():
            '''
            If the tracking header is set, save the request
            '''
            if flask.request.headers.get(self.TRACKING_HEADER):
                self._tracked_requests[flask.request.headers[self.TRACKING_HEADER]] = {'request': flask.request}

        @self.app.after_request
        def save_response(response):
            '''
            If the tracking header is set, save the response
            '''
            if flask.request.headers.get(self.TRACKING_HEADER):
                self._tracked_requests[flask.request.headers[self.TRACKING_HEADER]]['response'] = response

            return response

        @self.app.route('/', defaults={'path': ''})
        @self.app.route('/<path:path>')
        def catch_all(path=''):
            # get path key
            if path in self._handlers:
                return self._handlers[path](flask.request)

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
        key = str(len(self._tracked_requests))
        self._tracked_requests[key] = {}
        return key

    def get_tracking_by_key(self, key):
        '''
        Return tracking data by key
        '''
        if key not in self._tracked_requests:
            raise Exception()
        return self._tracked_requests[key]

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
        if path in self._handlers:
            raise Exception()
        self._handlers[path] = func

    def remove_handler(self, path):
        '''
        remove a handler attached to a specific path
        '''
        path = self.normalize_path(path)
        if path not in self._handlers:
            raise Exception()
        del self._handlers[path]

    def clear_handlers(self):
        '''
        Clear all handlers that have been registered
        '''
        self._handlers = {}

    def url(self, path=''):
        '''
        Get the url for the given path in this endpoint
        '''
        if path and not path.startswith('/'):
            path = '/' + path
        return 'http://127.0.0.1:{0}{1}'.format(self.address[1], path)

    def run(self):
        try:
            self.server = make_server('',
                                      self.port,
                                      self.app.wsgi_app)
            # mark the socket as SO_REUSEADDR
            self.server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except Exception as e:
            self.error = e
            self.ready.set()
            return
        # mark it as ready
        self.ready.set()
        # serve it
        self.server.serve_forever()


class TrackingWSGIServer(threading.Thread):
    '''
    A threaded webserver which will wrap any wsgi app and track request/response
    headers to the origin

        # create the thread object
        http_endpoint = tsqa.endpoint.TrackingWSGIServer(app)
        # start the thread
        http_endpoint.start()
        # wait for the webserver to listen
        http_endpoint.ready.wait()
    '''
    TRACKING_HEADER = '__cool_test_header__'  # TODO: better name?

    @property
    def address(self):
        '''
        Return a tuple of (ip, port) that this thread is listening on.
        '''
        return (self.server.server_address, self.server.server_port)

    def __init__(self, app, port=0):
        threading.Thread.__init__(self)
        # dict to store request data in
        self._tracked_requests = {}

        self.daemon = True
        self.port = port
        self.ready = threading.Event()

        self.app = app
        self.app.debug = True

        @self.app.before_request
        def save_request():
            '''
            If the tracking header is set, save the request
            '''
            if flask.request.headers.get(self.TRACKING_HEADER):
                self._tracked_requests[flask.request.headers[self.TRACKING_HEADER]] = {'request': request.copy()}


        @self.app.after_request
        def save_response(response):
            '''
            If the tracking header is set, save the response
            '''
            if flask.request.headers.get(self.TRACKING_HEADER):
                self._tracked_requests[flask.request.headers[self.TRACKING_HEADER]]['response'] = response

            return response

    def get_tracking_key(self):
        '''
        Return a new key for tracking a request by key
        '''
        key = str(len(self._tracked_requests))
        self._tracked_requests[key] = {}
        return key

    def get_tracking_by_key(self, key):
        '''
        Return tracking data by key
        '''
        if key not in self._tracked_requests:
            raise Exception()
        return self._tracked_requests[key]

    def run(self):
        self.server = make_server('',
                                  self.port,
                                  self.app.wsgi_app)
        # mark it as ready
        self.ready.set()
        # serve it
        self.server.serve_forever()


class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass


class SocketServerDaemon(threading.Thread):
    '''
    A daemon thread to run a socketserver
    '''
    def __init__(self, handler, port=0):
        threading.Thread.__init__(self)
        self.port = port
        self.handler = handler
        self.ready = threading.Event()
        self.daemon = True

    def run(self):
        self.server = ThreadedTCPServer(('0.0.0.0', self.port), self.handler)
        self.server.allow_reuse_address = True
        self.port = self.server.socket.getsockname()[1]

        self.ready.set()

        # Activate the server; this will keep running until you
        # interrupt the program with Ctrl-C
        self.server.serve_forever()


class ThreadedSSLTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    def __init__(self,
                 server_address,
                 RequestHandlerClass,
                 certfile,
                 keyfile,
                 ssl_version=ssl.PROTOCOL_TLSv1,
                 bind_and_activate=True):
        SocketServer.TCPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)
        self.certfile = certfile
        self.keyfile = keyfile
        self.ssl_version = ssl_version

    def get_request(self):
        newsocket, fromaddr = self.socket.accept()
        connstream = ssl.wrap_socket(newsocket,
                                     server_side=True,
                                     certfile=self.certfile,
                                     keyfile=self.keyfile,
                                     ssl_version=self.ssl_version,
                                     )
        return connstream, fromaddr

class SSLSocketServerDaemon(threading.Thread):
    '''
    A daemon thread to run a socketserver

    This is just a thread wrapper to https://docs.python.org/2/library/socketserver.html
    '''
    def __init__(self, handler, cert, key, port=0):
        '''
        handler: instance of SocketServer.BaseRequestHandler
            https://docs.python.org/2/library/socketserver.html#socketserver-tcpserver-example
        cert: path to certificate file
        key: path to key file
        '''
        # for testing it is *very* common to have self-signed certs, so we
        # will disable warnings so we don't flood logs
        requests.packages.urllib3.disable_warnings()

        threading.Thread.__init__(self)
        self.handler = handler
        self.cert = cert
        self.key = key
        self.port = port

        self.ready = threading.Event()
        self.daemon = True

    def run(self):
        self.server = ThreadedSSLTCPServer(('0.0.0.0', self.port),
                                           self.handler,
                                           self.cert,
                                           self.key,
                                           )
        self.server.allow_reuse_address = True
        self.port = self.server.socket.getsockname()[1]
        self.ready.set()

        self.server.serve_forever()
