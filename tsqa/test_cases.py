'''
Some base test cases that do environment handling for you
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

import logging
import os
import warnings

import httpbin

import tsqa.endpoint
import tsqa.environment
import tsqa.configs
import tsqa.utils
import plugin.conf_plugin
unittest = tsqa.utils.import_unittest()



# Base environment case
class EnvironmentCase(unittest.TestCase):
    '''
    This class will:
        - get a unique environment (using getEnv())
        - create wrappers for ATS configs available in self.configs
        - setup the environment (setUpEnv())
        - write out the configs
        - start the environment (environment.start())
    '''
    # TODO: better naming??
    environment_factory = {'configure': None,
                           'env': None,
                           }

    def run(self, result=None):
        unittest.TestCase.run(self, result)
        # we want to keep track of failures at a class level-- not instance level
        self.__class__.__successful &= result.result.wasSuccessful()

    @classmethod
    def setUpClass(cls):
        # call parent constructor
        super(EnvironmentCase, cls).setUpClass()

        # get a logger
        cls.log = logging.getLogger(__name__)

        # get an environment
        cls.environment = cls.getEnv()
        # TODO: better... I dont think this output is captured in each test run
        logging.info('Environment prefix is {0}'.format(cls.environment.layout.prefix))

        cfg_dir = os.path.join(cls.environment.layout.prefix, 'etc', 'trafficserver')

        # create a bunch of config objects that people can access/modify
        # classes that override our default config naming
        config_classes = {'records.config': tsqa.configs.RecordsConfig}
        # create a mapping of config-name -> config-obj
        cls.configs = {}
        for name in os.listdir(cls.environment.layout.sysconfdir):
            path = os.path.join(cls.environment.layout.sysconfdir, name)
            if os.path.isfile(path):
                cls.configs[name] = config_classes.get(name, tsqa.configs.Config)(path)

        # call env setup, so people can change configs etc
        cls.setUpEnv(cls.environment)

        for cfg in cls.configs.itervalues():
            cfg.write()

        # start ATS
        cls.environment.start()

        # we assume the tests passed
        cls.__successful = True

    @classmethod
    def getEnv(cls):
        '''
        This function is responsible for returning an environment. The default
        is to build ATS and return a copy of an environment
        '''
        SOURCE_DIR = os.getenv('TSQA_SRC_DIR', '~/trafficserver')
        TMP_DIR = os.getenv('TSQA_TMP_DIR','/tmp/tsqa')
        ef = tsqa.environment.EnvironmentFactory(SOURCE_DIR, os.path.join(TMP_DIR, 'base_envs'))
        return ef.get_environment(cls.environment_factory['configure'], cls.environment_factory['env'])

    @classmethod
    def setUpEnv(cls, env):
        '''
        This funciton is responsible for setting up the environment for this fixture
        This includes everything pre-daemon start (configs, certs, etc.)
        '''
        pass

    @classmethod
    def tearDownClass(cls):
        if not cls.environment.running():
            raise Exception('ATS died during the test run')
        # stop ATS
        cls.environment.stop()

        # call parent destructor
        super(EnvironmentCase, cls).tearDownClass()
        # if the test was successful, tear down the env
        if cls.__successful and (hasattr(plugin.conf_plugin, 'args') and ((not plugin.conf_plugin.args.keep_env) or (plugin.conf_plugin.args.keep_env is False))):
            cls.environment.destroy()  # this will tear down any processes that we started

    # Some helpful properties
    @property
    def proxies(self):
        '''
        Return a dict of schema -> proxy. This is primarily used for requests
        '''
        # TODO: create a better dict by parsing the config-- to handle http/https ports in the string
        return {'http': 'http://127.0.0.1:{0}'.format(self.configs['records.config']['CONFIG']['proxy.config.http.server_ports'])}


class DynamicHTTPEndpointCase(unittest.TestCase):
    '''
    This class will set up a dynamic http endpoint that is local to this class
    '''
    endpoint_port = 0
    @classmethod
    def setUpClass(cls):
        # get a logger
        cls.log = logging.getLogger(__name__)

        cls.http_endpoint = tsqa.endpoint.DynamicHTTPEndpoint(port=cls.endpoint_port)
        cls.http_endpoint.start()

        cls.http_endpoint.ready.wait()

        # Do this last, so we can get our stuff registered
        # call parent constructor
        super(DynamicHTTPEndpointCase, cls).setUpClass()

    def endpoint_url(self, path=''):
        '''
        Get the url for the local dynamic endpoint given a path
        '''
        return self.http_endpoint.url(path)


class HTTPBinCase(unittest.TestCase):
    '''
    This class will set up httpbin which is local to this class
    '''
    @classmethod
    def setUpClass(cls):
        # get a logger
        cls.log = logging.getLogger(__name__)

        cls.http_endpoint = tsqa.endpoint.TrackingWSGIServer(httpbin.app)
        cls.http_endpoint.start()

        cls.http_endpoint.ready.wait()

        # create local requester object
        cls.track_requests = tsqa.endpoint.TrackingRequests(cls.http_endpoint)

        # Do this last, so we can get our stuff registered
        # call parent constructor
        super(HTTPBinCase, cls).setUpClass()

    def endpoint_url(self, path=''):
        '''
        Get the url for the local dynamic endpoint given a path
        '''
        warnings.warn(('"endpoint_url" has been deprecated. The same function is '
                       'available under "http_endpoint.url"'))
        if path and not path.startswith('/'):
            path = '/' + path
        return 'http://127.0.0.1:{0}{1}'.format(self.http_endpoint.address[1],
                                                path)

