'''
Examples of how to use EnvironmentCase
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


class HelloWorld(tsqa.test_cases.EnvironmentCase):
    '''
    This is the trivial example of a TestCase. The parent class (in this case
    EnvironmentCase) is responsible for all the heavy lifting. By the time
    test_base is called EnvironmentCase will have aquired a unique environment,
    configured ATS, and started ATS.
    '''
    def test_base(self):
        # for example, you could send a request to ATS and check the response
        ret = requests.get('http://127.0.0.1:{0}/'.format(self.configs['records.config']['CONFIG']['proxy.config.http.server_ports']))

        # you also have access to your own logger.
        self.log('Something interesting to log')

        self.assertEqual(ret.status_code, 404)
        self.assertIn('ATS', ret.headers['server'], 'message to print on test failure')


class OverrideConfigureFlags(tsqa.test_cases.EnvironmentCase):
    '''
    The default getEnv() uses EnvironmentFactory to build trafficserver from
    source with given environment/configure options. You can override these
    values for a test class using the attribute "environment_factory"
    '''
    # Override the build options for environment factory
    environment_factory = {
        'env': {'ENV_VAR': 'VALUE'},
        'configure': {'enable-spdy': None},
    }


class FeatureRequirement(tsqa.test_cases.CloneEnvironmentCase):
    '''
    CloneEnvironmentCase will clone an environment (instead of building). You can
    declare dependencies on various features in trafficserver based on the output
    from traffic_layout. If the requirements aren't met your test will be skipped
    '''
    feature_requirements = {'TS_HAS_WCCP': 0}


class ConfiguredCase(tsqa.test_cases.EnvironmentCase):
    '''
    This is the trivial example of a TestCase. The parent class (in this case
    EnvironmentCase) is responsible for all the heavy lifting. By the time
    test_base is called EnvironmentCase will have aquired a unique environment,
    configured ATS, and started ATS.
    '''
    @classmethod
    def setUpEnv(cls, env):
        '''
        This funciton is responsible for setting up the environment for this fixture
        This includes everything pre-daemon start.

        You are passed in cls (which is the instance of this class) and env (which
        is an environment object)
        '''
        # we can modify any/all configs (note: all pre-daemon start)
        cls.configs['remap.config'].add_line('map / http://http://trafficserver.readthedocs.org/')

        # Some configs have nicer wrapper objects to give you a more pythonic interface
        cls.configs['records.config']['CONFIG'].update({
            'proxy.config.log.squid_log_enabled': 1,
            'proxy.config.log.squid_log_is_ascii': 1,
        })
