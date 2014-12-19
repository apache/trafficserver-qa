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
import time

class TestEnvironmentCase(tsqa.test_cases.EnvironmentCase):
    def test_base(self):
        assert isinstance(self.environment, tsqa.environment.Environment)

    # TODO: actually test this, this is currently terrible ;)
    def test_daemon(self):
        self.environment.start()  # start ATS
        time.sleep(2)
        assert self.environment.cop.pid > 0
        assert self.environment.cop.returncode is None
        self.environment.stop()

class TestDynamicHTTPEndpointCase(tsqa.test_cases.DynamicHTTPEndpointCase):
    def test_base(self):
        ret = requests.get(self.endpoint_url('/footest'))
        self.assertEqual(ret.status_code, 404)

    def test_endpoint_url(self):
        assert self.endpoint_url() == 'http://127.0.0.1:{0}'.format(self.http_endpoint.address[1])

        assert self.endpoint_url('/foo') == 'http://127.0.0.1:{0}/foo'.format(self.http_endpoint.address[1])


if __name__ == "__main__":
    unittest.main()
