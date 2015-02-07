'''
Test the buildcache
'''

import tsqa.utils
unittest = tsqa.utils.import_unittest()

import tempfile
import shutil
import os
import json


class TestBuildCache(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    @property
    def cache_map_file(self):
        return os.path.join(self.tmp_dir, tsqa.utils.BuildCache.cache_map_filename)

    def test_base(self):
        cache = tsqa.utils.BuildCache(self.tmp_dir)
        self.assertEqual(cache, {})
        cache.save_cache()
        self.assertTrue(os.path.exists(self.cache_map_file))
        cache.load_cache()
        self.assertEqual(cache, {})

    def test_load_cache(self):
        # make sure that a bad cache file gets emptied
        with open(self.cache_map_file, 'w') as fh:
            fh.write(json.dumps({'foo': {}}))

        cache = tsqa.utils.BuildCache(self.tmp_dir)
        self.assertEqual(cache, {})

    def test_save_cache(self):
        cache = tsqa.utils.BuildCache(self.tmp_dir)
        cache['foo'] = {'a': 'somepath'}

        with open(self.cache_map_file) as fh:
            json_cache = json.load(fh)
        self.assertEqual(json_cache, {'foo': {'a': 'somepath'}})



