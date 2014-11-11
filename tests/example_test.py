'''
This is a terrible example of how you would write some tests for tsqa
'''

import helpers
import tsqa


def test_example():
    assert True == True

class TestExample(helpers.TestCase):
    def test_example(self):
        assert True == True

