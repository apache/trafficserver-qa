'''
'''
import helpers

import tsqa.utils
unittest = tsqa.utils.import_unittest()
import tsqa.endpoint

import requests

class TestDynamicHTTPEndpoint(unittest.TestCase):
    def setUp(self):
        self.endpoint = tsqa.endpoint.DynamicHTTPEndpoint()
        self.endpoint.start()
        self.endpoint.ready.wait()

    def tearDown(self):
        self.endpoint.server.shutdown()

    def test_url(self):
        '''
        Test the "url" method, to ensure it returns the correct url
        '''
        self.assertEqual(self.endpoint.url(), 'http://127.0.0.1:{0}'.format(self.endpoint.address[1]))

        self.assertEqual(self.endpoint.url('/foo'), 'http://127.0.0.1:{0}/foo'.format(self.endpoint.address[1]))

    def test_normalize_path(self):
        self.assertEqual(self.endpoint.normalize_path('foo'), 'foo')
        self.assertEqual(self.endpoint.normalize_path('/foo'), 'foo')

    def test_handlers(self):
        # make sure we get 404s
        ret = requests.get(self.endpoint.url('/echo'))
        self.assertEqual(ret.status_code, 404)

        def echo(r):
            return 'echo'

        # check that echo works
        self.endpoint.add_handler('/echo', echo)
        ret = requests.get(self.endpoint.url('/echo'))
        self.assertEqual(ret.text, 'echo')

        # remove echo
        self.endpoint.remove_handler('/echo')

        # make sure its removed
        ret = requests.get(self.endpoint.url('/echo'))
        self.assertEqual(ret.status_code, 404)

        # re-add echo
        self.endpoint.add_handler('/echo', echo)
        ret = requests.get(self.endpoint.url('/echo'))
        self.assertEqual(ret.text, 'echo')

        # clear all, ensure its cleared
        self.endpoint.clear_handlers()
        ret = requests.get(self.endpoint.url('/echo'))
        self.assertEqual(ret.status_code, 404)


class TestTrackingRequests(unittest.TestCase):
    def setUp(self):
        self.endpoint = tsqa.endpoint.DynamicHTTPEndpoint()
        self.endpoint.start()
        self.endpoint.ready.wait()

        self.track = tsqa.endpoint.TrackingRequests(self.endpoint)

    def tearDown(self):
        self.endpoint.server.shutdown()

    def test_basic(self):
        ret = self.track.get(self.endpoint.url('/echo'))
        # TODO: test the request?? This requires some intermediate objects
        self.assertEqual(ret['client_response'].status_code, ret['server_response'].status_code)
