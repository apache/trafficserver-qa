'''
Examples of how to skip tests
    More examples: https://docs.python.org/2/library/unittest.html#unittest-skipping
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
import helpers


class SkipEntireClass(helpers.EnvironmentCase):
    @classmethod
    def setUpClass(cls):
        '''
        If you'd like to skip an entire test
        '''
        # If you raise SkipTest in setUpClass (or within a test case) the test
        # will be skipped. You can build logic around this to conditionally
        # skip tests based on environment conditions.
        raise unittest.SkipTest('Skip the entire class')


class SkipSingleTestCase(helpers.EnvironmentCase):
   @unittest.skip('Always skip this test with this message')
   def test_example(self):
        self.assertTrue(False)

