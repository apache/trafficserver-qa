'''
Test the utils
'''

import tsqa.utils
unittest = tsqa.utils.import_unittest()

class TestUtils(unittest.TestCase):
    def test_merge_dicts(self):
        '''
        These dicts should be merged in order, meaning latter ones will override
        earlier ones.
        '''
        self.assertEqual(tsqa.utils.merge_dicts({'a': 1}, {'a': 2}), {'a': 2})
        self.assertEqual(tsqa.utils.merge_dicts({'a': 1}, {'b': 2}), {'a': 1, 'b': 2})

    def test_configure_list(self):
        '''
        Test that we can convert a dict to a list of configure strings
        '''
        self.assertEqual(tsqa.utils.configure_list({'a': 'b', 'c': None}), ['--a=b', '--c'])

    def test_configure_string_to_dict(self):
        '''
        Can we reverse it?
        '''
        self.assertEqual(tsqa.utils.configure_string_to_dict('--a'), {'a': None})
        self.assertEqual(tsqa.utils.configure_string_to_dict('--a=b'), {'a': 'b'})
        self.assertEqual(tsqa.utils.configure_string_to_dict('--a=b --c'), {'a': 'b', 'c': None})

