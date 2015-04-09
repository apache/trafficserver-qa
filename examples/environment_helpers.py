'''
Environment cases will by default pull source from ~/trafficserver. For most
applications you will want to create a sub-class of tsqa.traffic_tests.EnvironmentCase
which will override the getEnv() method.
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


class HelperEnvironmentCase(tsqa.test_cases.EnvironmentCase):
    '''
    This is an example of how to subclass EnviromentCase and return your own
    environments. This one is pulled from the ATS core.
    '''
    @classmethod
    def getEnv(cls):
        '''
        This function is responsible for returning a unique environment
        '''
        SOURCE_DIR = os.path.realpath(os.path.join(__file__, '..', '..', '..', '..'))
        TMP_DIR = os.path.join(tempfile.gettempdir(), 'tsqa')
        ef = tsqa.environment.EnvironmentFactory(SOURCE_DIR,
                                                 os.path.join(TMP_DIR, 'base_envs'),
                                                 default_configure={'enable-example-plugins': None,
                                                                    'enable-test-tools': None,
                                                                    'enable-example-plugins': None,
                                                                    },
                                                 )
        # anywhere in this method you can raize SkipTest, and the test will be skipped
        # in this example we skip any exceptions in building the environment,
        # but you can put any logic in here to determine when a test should be
        # skipped (primarily if you can't provide the environment requested)
        try:
            return ef.get_environment(cls.environment_factory['configure'], cls.environment_factory['env'])
        except Exception as e:
            raise unittest.SkipTest(e)


class StaticEnvironmentCase(tsqa.test_cases.EnvironmentCase):
    '''
    This is an example which returns a static environment for all tests to run
    with. This is useful for testing specific builds of ATS or its plugins.

    An example would be to test a new internal plugin against the current internal
    build of ATS.
    '''
    @classmethod
    def getEnv(cls):
        '''
        This function is responsible for returning a unique environment
        '''
        # create a layout from the static root we have
        layout = tsqa.environment.Layout('static/environment/dir')
        # create a new environment
        env = tsqa.environment.Environment()
        # clone the static layout we have
        env.clone(layout=layout)
        return env
