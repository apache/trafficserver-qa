'''
This is a terrible example of how you would write some tests for tsqa
'''

import tsqa.utils
unittest = tsqa.utils.import_unittest()

def test_example():
    assert True == True

class TestExample(unittest.TestCase):
    def test_example(self):
        assert True == True

