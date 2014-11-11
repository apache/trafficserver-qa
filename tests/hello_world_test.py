'''
This test is meant as a "hello world" of this test framework

This should:
    - Get an environment
    - Start ATS
    - Start a webserver
    - send a request through
    - check that it worked
'''
import tsqa.utils
unittest = tsqa.utils.import_unittest()
import tsqa.test_cases
import tsqa.environment

import requests

class TestEnvironmentCase(tsqa.test_cases.EnvironmentCase):
    def test_base(self):
        assert isinstance(self.environment, tsqa.environment.Environment)

class TestDynamicHTTPEndpointCase(tsqa.test_cases.DynamicHTTPEndpointCase):
    def test_base(self):
        ret = requests.get(self.endpoint_url('/footest'))
        assert ret.status_code == 200

    def test_endpoint_url(self):
        assert self.endpoint_url() == 'http://127.0.0.1:{0}'.format(self.http_endpoint.address[1])

        assert self.endpoint_url('/foo') == 'http://127.0.0.1:{0}/foo'.format(self.http_endpoint.address[1])


if __name__ == "__main__":
    unittest.main()
