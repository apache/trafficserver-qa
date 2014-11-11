'''
Test the utils
'''

from .. import helpers
import tsqa.utils

def test_merge_dicts():
    assert tsqa.utils.merge_dicts({'a': 1}, {'a': 2}) == {'a': 2}
    assert tsqa.utils.merge_dicts({'a': 1}, {'b': 2}) == {'a': 1, 'b': 2}

def test_configure_list():
    assert tsqa.utils.configure_list({'a': 'b', 'c': None}) == ['--a=b', '--c']

def test_configure_string_to_dict():
    assert tsqa.utils.configure_string_to_dict('--a') == {'a': None}
    assert tsqa.utils.configure_string_to_dict('--a=b') == {'a': 'b'}
    assert tsqa.utils.configure_string_to_dict('--a=b --c') == {'a': 'b', 'c': None}

