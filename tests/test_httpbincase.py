'''
'''
import helpers

import tsqa.utils
unittest = tsqa.utils.import_unittest()
import tsqa.test_cases

import requests

class TestBasic(tsqa.test_cases.HTTPBinCase):
    def test_endpoint_url(self):
        self.assertEqual(self.endpoint_url(), 'http://127.0.0.1:{0}'.format(self.http_endpoint.address[1]))

        self.assertEqual(self.endpoint_url('/foo'), 'http://127.0.0.1:{0}/foo'.format(self.http_endpoint.address[1]))

    def test_basic(self):
        ret = requests.get(self.endpoint_url('/ip'))
        self.assertEqual(ret.json()['origin'], '127.0.0.1')
