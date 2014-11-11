'''
Test the utils
'''

import tsqa.utils

def test_merge_dicts():
    '''
    These dicts should be merged in order, meaning latter ones will override
    earlier ones.
    '''
    assert tsqa.utils.merge_dicts({'a': 1}, {'a': 2}) == {'a': 2}
    assert tsqa.utils.merge_dicts({'a': 1}, {'b': 2}) == {'a': 1, 'b': 2}

def test_configure_list():
    '''
    Test that we can convert a dict to a list of configure strings
    '''
    assert tsqa.utils.configure_list({'a': 'b', 'c': None}) == ['--a=b', '--c']

def test_configure_string_to_dict():
    '''
    Can we reverse it?
    '''
    assert tsqa.utils.configure_string_to_dict('--a') == {'a': None}
    assert tsqa.utils.configure_string_to_dict('--a=b') == {'a': 'b'}
    assert tsqa.utils.configure_string_to_dict('--a=b --c') == {'a': 'b', 'c': None}

