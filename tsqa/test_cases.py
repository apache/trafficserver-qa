'''
Some base test cases that do environment handling for you
'''

import tsqa.endpoint
import tsqa.environment
import tsqa.utils
unittest = tsqa.utils.import_unittest()

import os


# Example environment case
class EnvironmentCase(unittest.TestCase):
    '''
    This class will get an environment (which is unique) but won't start it
    '''
    @classmethod
    def setUpClass(cls):
        # call parent constructor
        super(EnvironmentCase, cls).setUpClass()

        # get an environment
        cls.environment = cls.getEnv()

        # call env setup, so people can change configs etc
        cls.setUpEnv(cls.environment)

        # start ATS
        cls.environment.start()

    @classmethod
    def getEnv(cls):
        '''
        This function is responsible for returning an environment. The default
        is to build ATS and return a copy of an environment
        '''
        SOURCE_DIR = os.getenv('TSQA_SRC_DIR', '~/trafficserver')
        TMP_DIR = os.getenv('TSQA_TMP_DIR','/tmp/tsqa')
        ef = tsqa.environment.EnvironmentFactory(SOURCE_DIR, os.path.join(TMP_DIR, 'base_envs'))
        return ef.get_environment()

    @classmethod
    def setUpEnv(cls, env):
        '''
        This funciton is responsible for setting up the environment for this fixture
        This includes everything pre-daemon start (configs, certs, etc.)
        '''
        pass

    @classmethod
    def tearDownClass(cls):
        # stop ATS
        cls.environment.stop()

        # call parent destructor
        super(EnvironmentCase, cls).tearDownClass()
        cls.environment.destroy()  # this will tear down any processes that we started


class DynamicHTTPEndpointCase(unittest.TestCase):
    '''
    This class will set up a dynamic http endpoint that is local to this class
    '''
    @classmethod
    def setUpClass(cls, port=0):
        cls.http_endpoint = tsqa.endpoint.DynamicHTTPEndpoint(port=port)
        cls.http_endpoint.start()

        cls.http_endpoint.ready.wait()

        # create local requester object
        cls.track_requests = tsqa.endpoint.TrackingRequests(cls.http_endpoint)

        # Do this last, so we can get our stuff registered
        # call parent constructor
        super(DynamicHTTPEndpointCase, cls).setUpClass()

    def endpoint_url(self, path=''):
        '''
        Get the url for the local dynamic endpoint given a path
        '''
        if path and not path.startswith('/'):
            path = '/' + path
        return 'http://127.0.0.1:{0}{1}'.format(self.http_endpoint.address[1],
                                                path)

