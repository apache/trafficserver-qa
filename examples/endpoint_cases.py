'''
Examples of how to use DynamicHTTPEndpointCase
'''
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
import tsqa.test_cases
import requests


class TestDynamicHTTPEndpointCase(tsqa.test_cases.DynamicHTTPEndpointCase):
    '''
    DynamicHTTPEndpointCase will set up an instance attribute of "http_endpoint"
    as well as a method (endpoint_url) to generate http request strings from paths.
    '''
    def test_base(self):
        '''
        By default there are no handlers registered to the server thread, so
        all requests will 404
        '''
        ret = requests.get(self.endpoint_url('/footest'))
        self.assertEqual(ret.status_code, 404)

    def test_endpoint_url(self):
        '''
        self.endpoint_url is useful for converting paths into http request strings
        '''
        self.assertEqual(self.endpoint_url(), 'http://127.0.0.1:{0}'.format(self.http_endpoint.address[1]))

        self.assertEqual(self.endpoint_url('/foo'), 'http://127.0.0.1:{0}/foo'.format(self.http_endpoint.address[1]))

    def test_with_endpoint(self):
        '''
        You can register custom handlers to the http_endpoint
        '''
        # create a function which will take the Flask request object (http://werkzeug.pocoo.org/docs/0.10/wrappers/#werkzeug.wrappers.Request)
        # and return a valid return for Flask (http://flask.pocoo.org/docs/0.10/quickstart/#about-responses)
        def handler(request):
            return "hello world"

        # register the endpoint on a context path. Now any request to /hello will
        # be sent to the handler function specified
        self.http_endpoint.add_handler('/hello', handler)

        ret = requests.get(self.endpoint_url('/hello'))
        self.assertEqual(ret.text, 'hello world')
